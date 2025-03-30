# database/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.exc import OperationalError
from config.settings import DATABASE_URL
import logging
import time

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,   # Переподключение каждый час
    pool_size=10,        # Размер пула соединений
    max_overflow=20,     # Максимальное количество дополнительных соединений
    pool_timeout=30,     # Тайм-аут ожидания соединения
    echo=False           # Не выводить SQL-запросы в лог
)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

Base = declarative_base()


def get_db():
    """
    Функция-генератор для получения сессии базы данных с правильным управлением транзакциями.
    """
    db = None
    try:
        db = Session()
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        if db:
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logger.error(f"Error closing database connection: {close_error}")
        Session.remove()  # Важно! Освобождаем сессию из текущего потока