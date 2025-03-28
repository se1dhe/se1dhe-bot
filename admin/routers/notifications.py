# admin/routers/notifications.py

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Body
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from models.models import User, Order, OrderStatus, Bot, Changelog
from database.db import get_db
from bot.main import bot

router = APIRouter()

templates = Jinja2Templates(directory=Path("admin/templates"))


@router.post("/send")
async def send_notification(
        user_ids: List[int] = Body(...),
        message: str = Body(...),
        db: Session = Depends(get_db)
):
    """Отправка уведомления выбранным пользователям"""
    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No users selected"
        )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )

    # Получаем пользователей из БД
    users = db.query(User).filter(User.id.in_(user_ids)).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found with the provided IDs"
        )

    # Счетчики успешных и неуспешных отправок
    sent_count = 0
    failed_count = 0

    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1

    return {
        "success": True,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total_users": len(users)
    }


@router.post("/broadcast")
async def broadcast_notification(
        message: str = Body(...),
        filter_active: bool = Body(False),
        db: Session = Depends(get_db)
):
    """Отправка уведомления всем пользователям"""
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )

    # Получаем пользователей из БД
    query = db.query(User)

    # Если указан фильтр активных пользователей, добавляем условие
    if filter_active:
        # Здесь должна быть логика определения активных пользователей
        # Например, пользователи, которые взаимодействовали с ботом в течение последних 30 дней
        pass

    users = query.all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found"
        )

    # Счетчики успешных и неуспешных отправок
    sent_count = 0
    failed_count = 0

    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1

    return {
        "success": True,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total_users": len(users)
    }


# admin/routers/notifications.py (продолжение)

@router.post("/send_changelog")
async def send_changelog_notification(
        changelog_id: int = Body(...),
        db: Session = Depends(get_db)
):
    """Отправка уведомления о выходе новой версии бота"""
    # Получаем ченжлог из БД
    changelog = db.query(Changelog).filter(Changelog.id == changelog_id).first()

    if not changelog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog not found"
        )

    # Получаем бота из БД
    bot_item = db.query(Bot).filter(Bot.id == changelog.bot_id).first()

    if not bot_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Получаем всех пользователей, которые купили этого бота
    users_query = db.query(User).join(Order).filter(
        Order.bot_id == bot_item.id,
        Order.status == OrderStatus.PAID
    ).distinct()

    users = users_query.all()

    if not users:
        return {
            "success": True,
            "message": "No users found who purchased this bot",
            "sent_count": 0,
            "total_users": 0
        }

    # Формируем текст сообщения
    message = f"🆕 <b>Обновление бота {bot_item.name}</b>\n\n"
    message += f"<b>Версия {changelog.version}</b>\n\n"
    message += changelog.description

    # Если есть ссылка на инструкцию, добавляем её
    if bot_item.readme_url:
        message += f"\n\n<a href='{bot_item.readme_url}'>Подробная инструкция</a>"

    # Счетчики успешных и неуспешных отправок
    sent_count = 0
    failed_count = 0

    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1

    # Отмечаем, что уведомление отправлено
    if sent_count > 0:
        changelog.is_notified = True
        db.commit()

    return {
        "success": True,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total_users": len(users)
    }

# Регистрация роутера в admin/main.py
# В секции где регистрируются остальные API роутеры
# from admin.routers import notifications
# app.include_router(notifications.router, prefix="/notifications", tags=["notifications"], dependencies=[Depends(verify_token)])