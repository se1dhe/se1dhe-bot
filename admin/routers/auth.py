# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from pathlib import Path
from jose import jwt
from datetime import timedelta
from typing import Optional
import hmac
import hashlib
import time

from admin.midddleware.auth_middleware import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from database.db import Session
from models.models import User
from config.settings import ADMIN_IDS, SECRET_KEY


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

templates = Jinja2Templates(directory=Path("admin/templates"))


class Token(BaseModel):
    access_token: str
    token_type: str


class TelegramAuth(BaseModel):
    id: int
    first_name: str
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


def check_telegram_authorization(auth_data: dict) -> bool:
    """Проверяет данные авторизации от Telegram Login Widget"""
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data.items()) if k != 'hash'])
    secret_key = hashlib.sha256(SECRET_KEY.encode()).digest()
    hash_string = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Проверяем хеш и срок действия (не более 24 часов)
    return hash_string == auth_data['hash'] and time.time() - auth_data['auth_date'] < 86400


@router.get("/login")
async def login_page(request: Request):
    """Страница входа через Telegram"""
    return templates.TemplateResponse("auth/auth.html", {"request": request})


@router.post("/telegram-login")
async def telegram_login(auth_data: TelegramAuth):
    """Аутентификация через данные от Telegram Login Widget"""
    # Преобразуем Pydantic модель в словарь
    auth_dict = auth_data.dict()

    # Проверяем данные авторизации
    if not check_telegram_authorization(auth_dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication data"
        )

    # Проверяем, является ли пользователь администратором
    if auth_data.id not in ADMIN_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access admin panel"
        )

    # Получаем или создаем пользователя
    db = Session()
    try:
        user = db.query(User).filter(User.telegram_id == auth_data.id).first()
        if not user:
            user = User(
                telegram_id=auth_data.id,
                username=auth_data.username,
                first_name=auth_data.first_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    # Создаем JWT токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": auth_data.username or str(auth_data.id), "telegram_id": auth_data.id},
        expires_delta=access_token_expires
    )

    # Возвращаем токен
    return {"access_token": access_token, "token_type": "bearer", "user": {
        "id": auth_data.id,
        "username": auth_data.username,
        "first_name": auth_data.first_name,
        "photo_url": auth_data.photo_url
    }}


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Получение токена по логину и паролю (для OAuth2)"""
    # Поскольку мы используем Telegram для аутентификации,
    # эта функция только для совместимости с OAuth2PasswordBearer
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Use Telegram authentication instead"
    )


@router.get("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/auth/auth")
    return response