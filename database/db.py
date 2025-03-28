# database/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.exc import OperationalError
from config.settings import DATABASE_URL
import logging
import time

logger = logging.getLogger(__name__)

# Создаем движок базы данных с настройками пула соединений
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,  # Переподключение каждый час
    pool_size=10,  # Размер пула соединений
    max_overflow=20  # Максимальное количество дополнительных соединений
)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

Base = declarative_base()


def get_db():
    """
    Функция-генератор для получения сессии базы данных с правильным управлением транзакциями.
    Автоматически откатывает транзакцию в случае исключения и повторяет попытку подключения при потере соединения.
    """
    db = Session()
    try:
        yield db
    except OperationalError as e:
        # Если соединение потеряно, пробуем восстановить
        logger.error(f"Database connection error: {e}")
        db.rollback()

        # Пробуем переподключиться
        try:
            # Получаем новую сессию
            db.close()
            db = Session()
            yield db
        except Exception as reconnect_error:
            logger.error(f"Database reconnection error: {reconnect_error}")
            raise
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception as close_error:
            logger.error(f"Error closing database connection: {close_error}")