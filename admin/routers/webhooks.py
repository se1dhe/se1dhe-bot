# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any
import logging
from bot.handlers.payments import process_payment_notification

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)

logger = logging.getLogger(__name__)


@router.post("/freekassa")
async def freekassa_webhook(request: Request):
    """Обработчик webhooks от FreeKassa"""
    try:
        # Получаем данные запроса
        data = await request.form()
        notification_data = dict(data)

        logger.info(f"Received FreeKassa webhook: {notification_data}")

        # Обрабатываем уведомление
        result = await process_payment_notification(notification_data, 'freekassa')

        if not result.get('success'):
            return {"success": 0, "error": "Invalid notification data"}

        # Возвращаем успешный ответ в формате, который ожидает FreeKassa
        return {"success": 1}
    except Exception as e:
        logger.error(f"Error processing FreeKassa webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/paykassa")
async def paykassa_webhook(request: Request):
    """Обработчик webhooks от PayKassa"""
    try:
        # Получаем данные запроса
        payload = await request.json()

        logger.info(f"Received PayKassa webhook: {payload}")

        # Обрабатываем уведомление
        result = await process_payment_notification(payload, 'paykassa')

        if not result.get('success'):
            return {"error": 1, "message": "Invalid notification data"}

        # Возвращаем успешный ответ в формате, который ожидает PayKassa
        return {"error": 0, "message": "Success"}
    except Exception as e:
        logger.error(f"Error processing PayKassa webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )