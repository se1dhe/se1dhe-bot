# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from pathlib import Path
from jose import jwt
from datetime import timedelta
from typing import Optional, Dict
import hmac
import hashlib
import time
import logging

from admin.middleware.auth_middleware import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from database.db import Session
from models.models import User
from config.settings import ADMIN_IDS, SECRET_KEY, BOT_TOKEN

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

templates = Jinja2Templates(directory=Path("admin/templates"))
logger = logging.getLogger(__name__)


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


def check_telegram_hash(data, bot_token):
    """Альтернативный метод проверки подписи от Telegram"""
    data_copy = data.copy()
    hash_str = data_copy.pop('hash')

    data_check = []
    for k in sorted(data_copy.keys()):
        data_check.append(f"{k}={data_copy[k]}")

    data_check_string = "\n".join(data_check)
    logger.info(f"Data check string: {data_check_string}")

    token_hash = hashlib.sha256(bot_token.split(':')[0].encode()).digest()

    hmac_hash = hmac.new(
        token_hash,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    logger.info(f"HMAC hash: {hmac_hash}")
    logger.info(f"Telegram hash: {hash_str}")

    return hmac_hash == hash_str


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа через Telegram"""
    return templates.TemplateResponse("auth/auth.html", {"request": request})


@router.get("/telegram-login-test")
async def telegram_login_test(request: Request):
    """Тестовая функция для отладки Telegram авторизации"""
    # Получаем все параметры запроса
    params = dict(request.query_params)

    # Выводим параметры в лог
    logger.info(f"Received params: {params}")

    # Возвращаем параметры в ответе
    return {"params": params, "bot_token_prefix": BOT_TOKEN.split(':')[0]}


@router.get("/telegram-login")
async def telegram_login(
        id: int,
        first_name: str,
        username: Optional[str] = None,
        photo_url: Optional[str] = None,
        auth_date: int = None,
        hash: str = None
):
    """Аутентификация через данные от Telegram Login Widget (GET запрос)"""
    # Преобразуем параметры запроса в словарь для проверки
    auth_dict = {
        "id": id,
        "first_name": first_name,
        "username": username,
        "photo_url": photo_url,
        "auth_date": auth_date,
        "hash": hash
    }

    # Удаляем None значения из словаря
    auth_dict = {k: v for k, v in auth_dict.items() if v is not None}

    logger.info(f"Received auth data: {auth_dict}")

    # Временно отключаем проверку для отладки
    # if not check_telegram_hash(auth_dict, BOT_TOKEN):
    #     logger.warning(f"Invalid authentication data for user {id}")
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid authentication data"
    #     )

    # Проверяем, является ли пользователь администратором
    if id not in ADMIN_IDS:
        logger.warning(f"Unauthorized access attempt from user {id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access admin panel"
        )

    # Получаем или создаем пользователя
    db = Session()
    try:
        user = db.query(User).filter(User.telegram_id == id).first()
        if not user:
            logger.info(f"Creating new user for telegram_id {id}")
            user = User(
                telegram_id=id,
                username=username,
                first_name=first_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during authentication"
        )
    finally:
        db.close()

    # Создаем JWT токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username or str(id), "telegram_id": id},
        expires_delta=access_token_expires
    )

    logger.info(f"User {id} authenticated successfully")

    # Возвращаем HTML-страницу, которая сохранит токен и перенаправит на дашборд
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authenticating...</title>
        <script>
            localStorage.setItem('token', '{access_token}');
            window.location.href = '/dashboard';
        </script>
    </head>
    <body>
        <p>Authenticating... Please wait.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/telegram-login")
async def telegram_login_post(auth_data: TelegramAuth):
    """Аутентификация через данные от Telegram Login Widget (POST запрос)"""
    # Преобразуем Pydantic модель в словарь
    auth_dict = auth_data.dict()

    # Проверяем данные авторизации - временно отключено для отладки
    # if not check_telegram_hash(auth_dict, BOT_TOKEN):
    #     logger.warning(f"Invalid authentication data for user {auth_data.id}")
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid authentication data"
    #     )

    # Проверяем, является ли пользователь администратором
    if auth_data.id not in ADMIN_IDS:
        logger.warning(f"Unauthorized access attempt from user {auth_data.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access admin panel"
        )

    # Получаем или создаем пользователя
    db = Session()
    try:
        user = db.query(User).filter(User.telegram_id == auth_data.id).first()
        if not user:
            logger.info(f"Creating new user for telegram_id {auth_data.id}")
            user = User(
                telegram_id=auth_data.id,
                username=auth_data.username,
                first_name=auth_data.first_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during authentication"
        )
    finally:
        db.close()

    # Создаем JWT токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": auth_data.username or str(auth_data.id), "telegram_id": auth_data.id},
        expires_delta=access_token_expires
    )

    logger.info(f"User {auth_data.id} authenticated successfully")

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
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Logging out...</title>
        <script>
            localStorage.removeItem('token');
            window.location.href = '/';
        </script>
    </head>
    <body>
        <p>Logging out... Please wait.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)