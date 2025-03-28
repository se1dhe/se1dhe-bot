# -*- coding: utf-8 -*-
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from config.settings import SECRET_KEY, ADMIN_IDS
from database.db import Session
from models.models import User
import logging

logger = logging.getLogger(__name__)

# Настройки JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Эти пути не требуют проверки токена
PUBLIC_PATHS = [
    "/",
    "/auth/login",
    "/auth/logout",
    "/auth/telegram-login",
    "/auth/token",
    "/webhooks/freekassa",
    "/webhooks/paykassa"
]


class TokenData(BaseModel):
    username: Optional[str] = None
    telegram_id: Optional[int] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создаёт JWT токен"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str = Depends(oauth2_scheme)):
    """Проверяет JWT токен и возвращает данные пользователя"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Декодируем JWT токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        telegram_id = payload.get("telegram_id")

        if username is None or telegram_id is None:
            raise credentials_exception

        token_data = TokenData(username=username, telegram_id=telegram_id)

    except JWTError:
        raise credentials_exception

    # Проверяем, является ли пользователь администратором
    if int(token_data.telegram_id) not in ADMIN_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )

    # Получаем пользователя из базы данных
    db = Session()
    try:
        user = db.query(User).filter(User.telegram_id == token_data.telegram_id).first()
        if user is None:
            raise credentials_exception
    finally:
        db.close()

    return user


async def get_token_from_request(request: Request) -> Optional[str]:
    """Получает токен из различных источников в запросе"""
    # Сначала проверяем заголовок Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Убираем "Bearer "

    # Затем проверяем cookie
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        return token[7:]

    # Если нет токена нигде, возвращаем None
    return None


# Функция для проверки аутентификации в шаблонах
async def verify_auth_for_templates(request: Request):
    """Проверяет аутентификацию для шаблонных маршрутов"""

    # Проверяем, находится ли путь в списке публичных маршрутов
    if request.url.path in PUBLIC_PATHS:
        return True

    # Для статических файлов пропускаем проверку
    if request.url.path.startswith("/static/"):
        return True

    # Получаем токен из запроса
    token = await get_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        # Декодируем JWT токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        telegram_id = payload.get("telegram_id")

        if username is None or telegram_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        if int(telegram_id) not in ADMIN_IDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )

        return True
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )