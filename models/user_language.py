# -*- coding: utf-8 -*-
import logging
from typing import Dict, Optional
from config.settings import DEFAULT_LANGUAGE
from database.db import Session as DbSession
from models.models import User

logger = logging.getLogger(__name__)


class UserLanguage:
    """
    Класс для хранения и управления языковыми настройками пользователей.
    """

    def __init__(self):
        self.languages: Dict[int, str] = {}
        # Загружаем языковые настройки из базы данных при инициализации
        self._load_languages_from_db()

    def _load_languages_from_db(self):
        """Загружает языковые настройки пользователей из базы данных"""
        try:
            db = DbSession()
            users = db.query(User).all()
            for user in users:
                if user.language:
                    self.languages[user.telegram_id] = user.language
            logger.info(f"Loaded language settings for {len(self.languages)} users")
        except Exception as e:
            logger.error(f"Error loading language settings from database: {e}")
        finally:
            db.close()

    def set_language(self, user_id: int, language: str) -> None:
        """
        Устанавливает язык для пользователя.

        Args:
            user_id (int): ID пользователя
            language (str): Код языка
        """
        try:
            # Сохраняем в кеше
            self.languages[user_id] = language

            # Сохраняем в базе данных
            db = DbSession()
            try:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    user.language = language
                    db.commit()
                    logger.info(f"Saved language {language} for user {user_id} in database")
                else:
                    logger.warning(f"User {user_id} not found in database")
            finally:
                db.close()
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
        # Проверяем наличие в кеше
        if user_id in self.languages:
            return self.languages.get(user_id)

        # Если нет в кеше, пробуем получить из базы данных
        try:
            db = DbSession()
            try:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user and user.language:
                    self.languages[user_id] = user.language
                    return user.language
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting language for user {user_id}: {e}")

        return None

    def delete_language(self, user_id: int) -> None:
        """
        Удаляет языковые настройки пользователя.

        Args:
            user_id (int): ID пользователя
        """
        # Удаляем из кеша
        if user_id in self.languages:
            del self.languages[user_id]

        # Удаляем из базы данных (устанавливаем значение по умолчанию)
        try:
            db = DbSession()
            try:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    user.language = DEFAULT_LANGUAGE
                    db.commit()
                    logger.info(f"Reset language to default for user {user_id} in database")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error deleting language settings for user {user_id}: {e}")