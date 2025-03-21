# -*- coding: utf-8 -*-
import json
import logging
import os
from typing import Dict, Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from pathlib import Path
from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from models.user_language import UserLanguage

logger = logging.getLogger(__name__)


class I18nMiddleware(BaseMiddleware):
    """
    Middleware для интернационализации сообщений бота.
    Автоматически подставляет нужный язык в зависимости от настроек пользователя.
    """

    def __init__(self, bot_dir: str = "bot"):
        self.bot_dir = bot_dir
        self.messages = {}
        self.user_languages = UserLanguage()

        # Загружаем все файлы локализации
        self._load_translations()

    def _load_translations(self):
        """Загружает все файлы локализации из директории locales"""
        try:
            locales_dir = Path(self.bot_dir) / "locales"

            for lang in SUPPORTED_LANGUAGES:
                lang_file = locales_dir / lang / "messages.json"

                if not lang_file.exists():
                    logger.warning(f"Locale file not found: {lang_file}")
                    continue

                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.messages[lang] = json.load(f)
                    logger.info(f"Loaded translations for {lang}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in locale file: {lang_file}")
                except Exception as e:
                    logger.error(f"Error loading locale file {lang_file}: {e}")

        except Exception as e:
            logger.error(f"Error loading translations: {e}")

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает событие, добавляя функцию перевода в data.

        Args:
            handler: Обработчик события
            event: Сообщение или callback-запрос
            data: Данные события

        Returns:
            Any: Результат обработчика
        """
        # Определяем пользователя
        user = event.from_user

        # Проверяем есть ли у пользователя сохраненный язык
        user_lang = self.user_languages.get_language(user.id)

        # Если язык не сохранен, используем язык из настроек пользователя или по умолчанию
        if not user_lang:
            user_lang = user.language_code if user.language_code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

        # Добавляем функцию перевода в data
        data["i18n"] = self._get_translator(user_lang)

        # Продолжаем обработку события
        return await handler(event, data)

    def _get_translator(self, lang: str) -> Callable[[str, Dict[str, Any]], str]:
        """
        Возвращает функцию перевода для указанного языка.

        Args:
            lang (str): Код языка

        Returns:
            Callable: Функция перевода
        """

        def translator(key: str, kwargs: Dict[str, Any] = None) -> str:
            """
            Переводит ключ сообщения с подстановкой переменных.

            Args:
                key (str): Ключ сообщения
                kwargs (Dict[str, Any], optional): Переменные для подстановки

            Returns:
                str: Переведенное сообщение
            """
            if not kwargs:
                kwargs = {}

            # Получаем сообщение для указанного языка или для языка по умолчанию
            message = self.messages.get(lang, {}).get(key)

            # Если сообщение не найдено, пробуем получить его для языка по умолчанию
            if not message and lang != DEFAULT_LANGUAGE:
                message = self.messages.get(DEFAULT_LANGUAGE, {}).get(key)

            # Если сообщение все равно не найдено, возвращаем ключ
            if not message:
                return f"MISSING:{key}"

            # Подставляем переменные в сообщение
            try:
                return message.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing variable in translation: {e}")
                return message
            except Exception as e:
                logger.error(f"Error formatting translation: {e}")
                return message

        return translator