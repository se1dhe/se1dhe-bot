# -*- coding: utf-8 -*-
import telegraph
import logging
from config.settings import TELEGRAPH_TOKEN

logger = logging.getLogger(__name__)


def create_telegraph_page(title, content, author="SE1DHE Bot"):
    """
    Создаёт страницу в Telegraph и возвращает URL.

    Args:
        title (str): Заголовок страницы
        content (str): HTML-содержимое страницы
        author (str): Имя автора

    Returns:
        str: URL созданной страницы или None в случае ошибки
    """
    try:
        # Инициализируем клиент Telegraph
        telegraph_client = telegraph.Telegraph(TELEGRAPH_TOKEN)

        # Создаем страницу
        response = telegraph_client.create_page(
            title=title,
            html_content=content,
            author_name=author
        )

        # Получаем URL страницы
        url = f"https://telegra.ph/{response['path']}"
        logger.info(f"Created Telegraph page: {url}")
        return url

    except telegraph.exceptions.TelegraphException as e:
        logger.error(f"Telegraph API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while creating Telegraph page: {e}")
        return None


def edit_telegraph_page(path, title, content, author="SE1DHE Bot"):
    """
    Редактирует существующую страницу в Telegraph.

    Args:
        path (str): Путь страницы (часть URL после telegra.ph/)
        title (str): Новый заголовок страницы
        content (str): Новое HTML-содержимое страницы
        author (str): Имя автора

    Returns:
        bool: True если редактирование успешно, иначе False
    """
    try:
        # Инициализируем клиент Telegraph
        telegraph_client = telegraph.Telegraph(TELEGRAPH_TOKEN)

        # Извлекаем path из URL, если был передан полный URL
        if 'telegra.ph/' in path:
            path = path.split('telegra.ph/')[-1]

        # Редактируем страницу
        telegraph_client.edit_page(
            path=path,
            title=title,
            html_content=content,
            author_name=author
        )

        logger.info(f"Updated Telegraph page: {path}")
        return True

    except telegraph.exceptions.TelegraphException as e:
        logger.error(f"Telegraph API error while editing page: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while editing Telegraph page: {e}")
        return False