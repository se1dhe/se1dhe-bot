import hashlib
import hmac
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_telegram_auth(auth_data, token):
    """
    Проверяет подпись данных авторизации от Telegram.
    """
    # Извлекаем хеш из данных
    received_hash = auth_data.get('hash')
    if not received_hash:
        logger.error("Hash not found in auth data")
        return False

    # Создаем копию данных без хеша
    auth_data_copy = dict(auth_data)
    auth_data_copy.pop('hash', None)

    logger.info(f"Auth data without hash: {auth_data_copy}")
    logger.info(f"Bot token: {token}")

    # Формируем строку проверки с сортировкой по ключам
    data_check_arr = []
    for key in sorted(auth_data_copy.keys()):
        value = auth_data_copy[key]
        if value is not None:
            data_check_arr.append(f"{key}={value}")

    # Используем специальный символ \n (ASCII 0x0A) как разделитель
    data_check_string = chr(10).join(data_check_arr)

    # Выводим в лог в виде шестнадцатеричных кодов
    hex_representation = ' '.join(hex(ord(c))[2:] for c in data_check_string)
    logger.info(f"Data check string hex: {hex_representation}")

    # Получаем секретный ключ из токена бота
    token_secret = token.split(':')[0]
    secret_key = hashlib.sha256(token_secret.encode()).digest()

    logger.info(f"Token secret: {token_secret}")
    logger.info(f"Secret key (SHA256): {secret_key.hex()}")

    # Вычисляем HMAC-SHA256 хеш
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    logger.info(f"Computed hash: {computed_hash}")
    logger.info(f"Received hash: {received_hash}")
    logger.info(f"Hashes match: {computed_hash == received_hash}")

    return computed_hash == received_hash


def check_telegram_auth_php_style(auth_data, token):
    """
    Проверяет подпись данных авторизации от Telegram по аналогии с кодом PHP.
    """
    received_hash = auth_data.get('hash')
    if not received_hash:
        return False

    # Убираем hash из проверки
    auth_data_copy = auth_data.copy()
    auth_data_copy.pop('hash', None)

    # Формируем массив строк key=value
    data_check_arr = []
    for key, value in auth_data_copy.items():
        data_check_arr.append(f"{key}={value}")

    # Сортируем массив
    data_check_arr.sort()

    # Объединяем строки с символом \n между ними
    data_check_string = '\n'.join(data_check_arr)

    # Создаем секретный ключ
    secret_key = hashlib.sha256(token.split(':')[0].encode()).digest()

    # Вычисляем HMAC-SHA256
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    logger.info(f"PHP style check:")
    logger.info(f"Data check array: {data_check_arr}")
    logger.info(f"Data check string: {data_check_string}")
    logger.info(f"Computed hash: {computed_hash}")
    logger.info(f"Match: {computed_hash == received_hash}")

    return computed_hash == received_hash


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_telegram_auth.py <bot_token> <auth_data>")
        print(
            "Example: python test_telegram_auth.py 123456789:ABC-DEF 'id=123456789&first_name=Test&auth_date=1612345678&hash=abcdef'")
        return

    token = sys.argv[1]
    auth_string = sys.argv[2]

    # Парсинг строки запроса в словарь
    auth_data = {}
    params = auth_string.split('&')
    for param in params:
        key, value = param.split('=', 1)
        auth_data[key] = value

    logger.info(f"Parsed auth data: {auth_data}")

    # Проверка подписи
    result = check_telegram_auth(auth_data, token)
    print(f"Authentication result: {result}")

    # Дополнительная проверка в стиле PHP
    result_php = check_telegram_auth_php_style(auth_data, token)
    print(f"Authentication result (PHP style): {result_php}")


if __name__ == "__main__":
    main()