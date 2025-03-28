#!/usr/bin/env python
import os
from sqlalchemy import create_engine, text

# Получаем URL базы данных из переменной окружения или используем значение по умолчанию
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:1234@localhost/se1dhe_bot")

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)

# SQL для изменения колонки
sql = text("ALTER TABLE users MODIFY COLUMN telegram_id BIGINT NOT NULL;")

# Выполняем SQL-запрос
try:
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
    print("Таблица users успешно изменена! Поле telegram_id теперь типа BIGINT.")
except Exception as e:
    print(f"Ошибка при изменении таблицы: {e}")