# -*- coding: utf-8 -*-
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from config.settings import SECRET_KEY, ADMIN_IDS
from database.db import Session
from models.models import User

# Настройки JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


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