# -*- coding: utf-8 -*-
import logging
from typing import Dict, Optional
from config.settings import DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


class UserLanguage:
    """
    Класс для хранения и управления языковыми настройками пользователей.
    В реальном приложении данные бы хранились в базе данных.
    """

    def __init__(self):
        self.languages: Dict[int, str] = {}

    def set_language(self, user_id: int, language: str) -> None:
        """
        Устанавливает язык для пользователя.

        Args:
            user_id (int): ID пользователя
            language (str): Код языка
        """
        try:
            self.languages[user_id] = language
            logger.info(f"Set language {language} for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting language for user {user_id}: {e}")

    def get_language(self, user_id: int) -> Optional[str]:
        """
        Возвращает язык пользователя или None, если не установлен.

        Args:
            user_id (int): ID пользователя

        Returns:
            Optional[str]: Код языка или None
        """
        return self.languages.get(user_id)

    def delete_language(self, user_id: int) -> None:
        """
        Удаляет языковые настройки пользователя.

        Args:
            user_id (int): ID пользователя
        """
        if user_id in self.languages:
            del self.languages[user_id]
            logger.info(f"Deleted language settings for user {user_id}")