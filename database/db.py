# database/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.exc import OperationalError, InterfaceError
from config.settings import DATABASE_URL
import logging
import time
import contextlib

logger = logging.getLogger(__name__)

# Оптимизированные настройки для работы с MySQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=1800,  # Переподключение каждые 30 минут
    pool_size=5,  # Уменьшаем размер пула для стабильности
    max_overflow=10,  # Уменьшаем максимальное количество дополнительных соединений
    pool_timeout=30,  # Тайм-аут ожидания соединения
    echo=False,  # Не выводить SQL-запросы в лог
    isolation_level="READ COMMITTED"  # Уровень изоляции транзакций
)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

Base = declarative_base()


def get_db():
    """
    Функция-генератор для получения сессии базы данных с правильным управлением транзакциями.
    """
    db = None
    try:
        # Создаем новую сессию для каждого запроса
        db = Session()
        yield db
    except Exception as e:
        logger.error(f"Database error during request: {e}")
        if db:
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        raise
    finally:
        # Всегда закрываем сессию и убираем её из реестра
        if db:
            try:
                db.close()
            except Exception as close_error:
                logger.error(f"Error closing database connection: {close_error}")
            finally:
                # Обязательно удаляем сессию из реестра потоков
                Session.remove()


@contextlib.contextmanager
def db_session():
    """
    Контекстный менеджер для работы с сессией базы данных.
    Использование:
    with db_session() as session:
        # Работа с сессией
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error in context manager: {e}")
        raise
    finally:
        session.close()
        Session.remove()


def execute_with_retry(func, max_retries=3, retry_delay=1):
    """
    Выполнение функции с автоматическим повтором при ошибках соединения.

    Args:
        func: Функция для выполнения
        max_retries: Максимальное количество повторов
        retry_delay: Задержка между повторами в секундах

    Returns:
        Результат выполнения функции
    """
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            return func()
        except (OperationalError, InterfaceError) as e:
            last_exception = e
            retries += 1
            logger.warning(f"Database connection error (attempt {retries}/{max_retries}): {e}")
            if retries < max_retries:
                time.sleep(retry_delay)
                # Немного увеличиваем задержку с каждой попыткой
                retry_delay *= 1.5
        except Exception as e:
            # Другие ошибки просто пробрасываем дальше
            logger.error(f"Unexpected database error: {e}")
            raise

    # Если все попытки исчерпаны, выбрасываем последнее исключение
    if last_exception:
        logger.error(f"All retries failed. Last error: {last_exception}")
        raise last_exception