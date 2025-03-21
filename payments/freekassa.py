# -*- coding: utf-8 -*-
import hashlib
import logging
import requests
from typing import Dict, Optional
from fastapi import HTTPException, status
from config.settings import FREEKASSA_SHOP_ID, FREEKASSA_API_KEY, FREEKASSA_SECRET_KEY

logger = logging.getLogger(__name__)


class FreeKassa:
    """
    Класс для интеграции с платежной системой FreeKassa
    """

    def __init__(self):
        self.shop_id = FREEKASSA_SHOP_ID
        self.api_key = FREEKASSA_API_KEY
        self.secret_key = FREEKASSA_SECRET_KEY
        self.base_url = "https://api.freekassa.ru/v1"

    def generate_payment_link(self, order_id: int, amount: float, currency: str = "RUB",
                              email: Optional[str] = None, description: str = "Оплата бота") -> str:
        """
        Генерирует ссылку для оплаты через FreeKassa.

        Args:
            order_id (int): ID заказа в системе
            amount (float): Сумма к оплате
            currency (str): Валюта платежа (по умолчанию RUB)
            email (str, optional): Email пользователя
            description (str): Описание платежа

        Returns:
            str: Ссылка на страницу оплаты
        """
        try:
            amount_str = str(amount)
            # Формируем строку для подписи
            sign_string = f"{self.shop_id}:{amount_str}:{self.secret_key}:{currency}:{order_id}"
            sign = hashlib.md5(sign_string.encode()).hexdigest()

            # Формируем ссылку для оплаты
            payment_url = (
                f"https://pay.freekassa.ru/?m={self.shop_id}&oa={amount_str}"
                f"&o={order_id}&s={sign}&currency={currency}"
            )

            # Добавляем email если указан
            if email:
                payment_url += f"&em={email}"

            # Добавляем описание платежа
            if description:
                payment_url += f"&us_desc={description}"

            logger.info(f"Generated FreeKassa payment link for order {order_id}")
            return payment_url

        except Exception as e:
            logger.error(f"Error generating FreeKassa payment link: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating payment link: {str(e)}"
            )

    def verify_notification(self, data: Dict) -> bool:
        """
        Проверяет подпись уведомления о платеже от FreeKassa.

        Args:
            data (Dict): Данные уведомления

        Returns:
            bool: True если подпись верна
        """
        try:
            merchant_id = data.get('MERCHANT_ID')
            amount = data.get('AMOUNT')
            merchant_order_id = data.get('MERCHANT_ORDER_ID')
            sign = data.get('SIGN')

            if not all([merchant_id, amount, merchant_order_id, sign]):
                logger.warning("Missing required fields in FreeKassa notification")
                return False

            # Формируем строку для проверки подписи
            check_string = f"{merchant_id}:{amount}:{self.secret_key}:{merchant_order_id}"
            check_sign = hashlib.md5(check_string.encode()).hexdigest()

            if sign.lower() != check_sign.lower():
                logger.warning("Invalid FreeKassa notification signature")
                return False

            logger.info(f"Verified FreeKassa payment notification for order {merchant_order_id}")
            return True

        except Exception as e:
            logger.error(f"Error verifying FreeKassa notification: {e}")
            return False

    def check_payment_status(self, order_id: int) -> Dict:
        """
        Проверяет статус платежа через API FreeKassa.

        Args:
            order_id (int): ID заказа

        Returns:
            Dict: Информация о статусе платежа
        """
        try:
            # Формируем подпись для запроса
            sign_string = f"{self.shop_id}{self.api_key}{order_id}"
            sign = hashlib.md5(sign_string.encode()).hexdigest()

            # Отправляем API запрос
            response = requests.get(
                f"{self.base_url}/orders/{order_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Shop-Id": str(self.shop_id),
                    "Sign": sign
                }
            )

            if response.status_code != 200:
                logger.warning(f"FreeKassa API error: {response.text}")
                return {"success": False, "message": "API error", "status": "unknown"}

            data = response.json()
            logger.info(f"Checked payment status for order {order_id}: {data}")

            return {
                "success": True,
                "order_id": order_id,
                "status": data.get("status", "unknown"),
                "amount": data.get("amount", 0),
                "raw_data": data
            }

        except Exception as e:
            logger.error(f"Error checking FreeKassa payment status: {e}")
            return {"success": False, "message": str(e), "status": "error"}