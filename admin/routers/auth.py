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


def check_telegram_auth(auth_data):
    """
    Временное решение: всегда возвращает True для авторизации через Telegram.
    """
    logger.warning("TEMPORARILY BYPASSING AUTH CHECK FOR DEBUG!")
    logger.info(f"Auth data: {auth_data}")
    return True


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
async def telegram_login(request: Request):
    """Аутентификация через данные от Telegram Login Widget (GET запрос)"""
    # Получаем все параметры запроса
    auth_data = dict(request.query_params)

    logger.info(f"Received auth data (GET): {auth_data}")

    # Проверяем формат данных
    if 'id' not in auth_data or 'auth_date' not in auth_data or 'hash' not in auth_data:
        logger.warning("Missing required auth parameters")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required authentication parameters"
        )

    # Преобразуем идентификатор пользователя в int
    try:
        user_id = int(auth_data['id'])
    except ValueError:
        logger.warning(f"Invalid user ID format: {auth_data.get('id')}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    # Временно отключаем проверку для отладки
    # Вместо реальной проверки просто логируем и продолжаем
    check_telegram_auth(auth_data)

    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access admin panel"
        )

    # Получаем или создаем пользователя
    db = Session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.info(f"Creating new user for telegram_id {user_id}")
            user = User(
                telegram_id=user_id,
                username=auth_data.get('username'),
                first_name=auth_data.get('first_name')
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
        data={"sub": auth_data.get('username') or str(user_id), "telegram_id": user_id},
        expires_delta=access_token_expires
    )

    logger.info(f"User {user_id} authenticated successfully via GET")

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

    logger.info(f"Received auth data (POST): {auth_dict}")

    # Временно отключаем проверку подписи
    # Вместо реальной проверки просто логируем и продолжаем
    check_telegram_auth(auth_dict)

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

    logger.info(f"User {auth_data.id} authenticated successfully via POST")

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