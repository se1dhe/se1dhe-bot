import unittest
from unittest.mock import patch, MagicMock
from payments.freekassa import FreeKassa
from payments.paykassa import PayKassa
import hashlib


class TestPaymentSystems(unittest.TestCase):
    def test_freekassa_payment_link(self):
        """Тест генерации ссылки для оплаты через FreeKassa"""
        with patch.object(FreeKassa, 'shop_id', '12345'), \
                patch.object(FreeKassa, 'secret_key', 'test_secret'):
            freekassa = FreeKassa()
            payment_link = freekassa.generate_payment_link(
                order_id=1234,
                amount=100.0,
                currency="RUB"
            )

            # Проверка структуры URL
            self.assertIn("pay.freekassa.ru", payment_link)
            self.assertIn("m=12345", payment_link)
            self.assertIn("oa=100.0", payment_link)
            self.assertIn("o=1234", payment_link)
            self.assertIn("s=", payment_link)  # Проверка наличия подписи

    def test_verify_freekassa_notification(self):
        """Тест проверки подписи уведомления от FreeKassa"""
        # Создаем тестовые данные и патчим методы
        with patch.object(FreeKassa, 'shop_id', '12345'), \
                patch.object(FreeKassa, 'secret_key', 'test_secret'):
            freekassa = FreeKassa()

            # Создаем тестовые данные уведомления с неверной подписью
            notification_data = {
                "MERCHANT_ID": "12345",
                "AMOUNT": "100.0",
                "MERCHANT_ORDER_ID": "1234",
                "SIGN": "invalid_sign"
            }

            # Проверка должна вернуть False для неверной подписи
            self.assertFalse(freekassa.verify_notification(notification_data))

            # Создаем верную подпись
            check_string = f"{notification_data['MERCHANT_ID']}:{notification_data['AMOUNT']}:{freekassa.secret_key}:{notification_data['MERCHANT_ORDER_ID']}"
            correct_sign = hashlib.md5(check_string.encode()).hexdigest()

            # Обновляем данные с верной подписью
            notification_data["SIGN"] = correct_sign

            # Проверка должна вернуть True для верной подписи
            self.assertTrue(freekassa.verify_notification(notification_data))

    def test_check_payment_status(self):
        """Тест проверки статуса платежа в FreeKassa"""
        with patch.object(FreeKassa, 'shop_id', '12345'), \
                patch.object(FreeKassa, 'api_key', 'test_api_key'), \
                patch('requests.get') as mock_get:
            # Создаем мок ответа
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "order_id": "1234",
                "amount": 100.0,
                "currency": "RUB"
            }
            mock_get.return_value = mock_response

            freekassa = FreeKassa()
            result = freekassa.check_payment_status(1234)

            # Проверяем, что запрос был отправлен с правильными параметрами
            mock_get.assert_called_once()
            self.assertTrue(result["success"])
            self.assertEqual(result["order_id"], 1234)
            self.assertEqual(result["status"], "success")


class TestPayKassa(unittest.TestCase):
    def test_create_payment(self):
        """Тест создания платежа в PayKassa"""
        with patch.object(PayKassa, 'shop_id', '12345'), \
                patch.object(PayKassa, 'api_key', 'test_api_key'), \
                patch.object(PayKassa, '_make_api_request') as mock_api:
            # Создаем мок ответа от API
            mock_api.return_value = {
                "error": False,
                "message": "Success",
                "data": {
                    "invoice_id": "ABC123",
                    "url": "https://paykassa.app/payment/ABC123",
                    "amount": 100.0,
                    "currency": "RUB"
                }
            }

            paykassa = PayKassa()
            result = paykassa.create_payment(
                order_id=1234,
                amount=100.0,
                currency="RUB"
            )

            # Проверяем результат
            self.assertTrue(result["success"])
            self.assertEqual(result["payment_id"], "ABC123")
            self.assertIn("paykassa.app", result["payment_url"])
            self.assertEqual(result["amount"], 100.0)

    def test_verify_notification(self):
        """Тест проверки подписи уведомления от PayKassa"""
        with patch.object(PayKassa, 'secret_key', 'test_secret'):
            paykassa = PayKassa()

            # Создаем тестовые данные с неверной подписью
            notification_data = {
                "shop_id": "12345",
                "order_id": "1234",
                "amount": "100.0",
                "currency": "RUB",
                "sign": "invalid_sign"
            }

            # Проверка должна вернуть False для неверной подписи
            self.assertFalse(paykassa.verify_notification(notification_data))

            # Тестирование с верной подписью потребует полного воссоздания алгоритма подписи
            # что выходит за рамки этого тестового примера


if __name__ == "__main__":
    unittest.main()