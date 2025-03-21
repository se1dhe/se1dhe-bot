# -*- coding: utf-8 -*-
import hashlib
import logging
import requests
import time
import json
from typing import Dict, Optional, Union
from fastapi import HTTPException, status
from config.settings import PAYKASSA_SHOP_ID, PAYKASSA_API_KEY, PAYKASSA_SECRET_KEY

logger = logging.getLogger(__name__)


class PayKassa:
    """
    Класс для интеграции с платежной системой PayKassa
    """

    def __init__(self):
        self.shop_id = PAYKASSA_SHOP_ID
        self.api_key = PAYKASSA_API_KEY
        self.secret_key = PAYKASSA_SECRET_KEY
        self.api_url = "https://api.paykassa.app/v1"

    def _make_api_request(self, method: str, params: Dict) -> Dict:
        """
        Выполняет API запрос к PayKassa.

        Args:
            method (str): Метод API
            params (Dict): Параметры запроса

        Returns:
            Dict: Ответ API
        """
        try:
            # Добавляем обязательные параметры
            data = {
                "shop_id": self.shop_id,
                "api_key": self.api_key,
                "func": method
            }
            data.update(params)

            # Отправляем POST запрос
            response = requests.post(self.api_url, json=data)
            response_data = response.json()

            if response.status_code != 200:
                logger.warning(f"PayKassa API error: {response_data}")
                return {"status": "error", "message": "API error", "data": response_data}

            logger.info(f"PayKassa API response for {method}: {response_data}")
            return response_data

        except Exception as e:
            logger.error(f"Error in PayKassa API request: {e}")
            return {"status": "error", "message": str(e)}

    def create_payment(self, order_id: int, amount: float, currency: str = "RUB",
                       system: str = "card_rub",
                       description: str = "Оплата бота",
                       user_email: Optional[str] = None) -> Dict:
        """
        Создает новый платеж в системе PayKassa.

        Args:
            order_id (int): ID заказа в системе
            amount (float): Сумма к оплате
            currency (str): Валюта платежа (по умолчанию RUB)
            system (str): Платежная система
            description (str): Описание платежа
            user_email (str, optional): Email пользователя

        Returns:
            Dict: Информация о созданном платеже, включая URL
        """
        try:
            params = {
                "amount": str(amount),
                "currency": currency,
                "order_id": str(order_id),
                "system": system,
                "comment": description,
                "phone": "",
                "paid_commission": "shop"  # Комиссия оплачивается магазином
            }

            if user_email:
                params["email"] = user_email

            # Выполняем API запрос
            response = self._make_api_request("sci_create_order_get_data", params)

            if response.get("error"):
                logger.warning(f"PayKassa payment creation error: {response}")
                return {"success": False, "message": response.get("message", "Unknown error")}

            # Возвращаем данные с URL для оплаты
            payment_data = response.get("data", {})
            return {
                "success": True,
                "payment_id": payment_data.get("invoice_id"),
                "payment_url": payment_data.get("url"),
                "amount": amount,
                "currency": currency,
                "order_id": order_id,
                "raw_data": payment_data
            }

        except Exception as e:
            logger.error(f"Error creating PayKassa payment: {e}")
            return {"success": False, "message": str(e)}

    def verify_notification(self, data: Dict) -> bool:
        """
        Проверяет подпись уведомления о платеже от PayKassa.

        Args:
            data (Dict): Данные уведомления

        Returns:
            bool: True если подпись верна
        """
        try:
            sign = data.get('sign')

            if not sign:
                logger.warning("Missing signature in PayKassa notification")
                return False

            # Копируем данные для формирования подписи
            check_data = data.copy()
            # Удаляем поле sign
            check_data.pop('sign', None)

            # Сортируем ключи
            sorted_data = {k: check_data[k] for k in sorted(check_data.keys())}

            # Формируем строку для подписи
            sign_string = ":".join([str(sorted_data[k]) for k in sorted_data]) + ":" + self.secret_key

            # Вычисляем подпись
            calculated_sign = hashlib.sha256(sign_string.encode()).hexdigest()

            if sign.lower() != calculated_sign.lower():
                logger.warning("Invalid PayKassa notification signature")
                return False

            logger.info(f"Verified PayKassa payment notification for order {data.get('order_id')}")
            return True

        except Exception as e:
            logger.error(f"Error verifying PayKassa notification: {e}")
            return False

    def check_payment_status(self, payment_id: Union[str, int]) -> Dict:
        """
        Проверяет статус платежа по его ID.

        Args:
            payment_id (str|int): ID платежа в системе PayKassa

        Returns:
            Dict: Информация о статусе платежа
        """
        try:
            params = {
                "shop_id": self.shop_id,
                "invoice_id": str(payment_id)
            }

            # Выполняем API запрос
            response = self._make_api_request("sci_confirm_order", params)

            if response.get("error"):
                logger.warning(f"PayKassa status check error: {response}")
                return {"success": False, "message": response.get("message", "Unknown error"), "status": "unknown"}

            # Получаем данные платежа
            payment_data = response.get("data", {})

            return {
                "success": True,
                "payment_id": payment_id,
                "order_id": payment_data.get("order_id"),
                "status": payment_data.get("status"),
                "amount": payment_data.get("amount"),
                "currency": payment_data.get("currency"),
                "raw_data": payment_data
            }

        except Exception as e:
            logger.error(f"Error checking PayKassa payment status: {e}")
            return {"success": False, "message": str(e), "status": "error"}