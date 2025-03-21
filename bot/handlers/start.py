# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.orm import Session
from models.models import User
from database.db import Session as DbSession
from datetime import datetime
from config.settings import DEFAULT_LANGUAGE
from bot.keyboards.main_menu import get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)


async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    Регистрирует нового пользователя или приветствует существующего
    """
    # Получаем информацию о пользователе из сообщения
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    language = message.from_user.language_code or DEFAULT_LANGUAGE

    # Проверяем есть ли пользователь в базе
    db = DbSession()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            # Создаем нового пользователя
            logger.info(f"Registering new user: {user_id}")
            user = User(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language=language
            )
            db.add(user)
            db.commit()

            # Получаем приветственное сообщение для нового пользователя
            welcome_text = _("welcome_new", message.from_user.language_code)
        else:
            # Обновляем информацию о пользователе
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.updated_at = datetime.utcnow()
            db.commit()

            # Получаем приветственное сообщение для существующего пользователя
            welcome_text = _("welcome_back", message.from_user.language_code)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        db.rollback()
        # Используем базовое приветствие в случае ошибки
        welcome_text = "Добро пожаловать в SE1DHE Bot! 🤖\n\nВыберите действие из меню ниже:"
    finally:
        db.close()

    # Отправляем приветственное сообщение и меню
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(message.from_user.language_code)
    )


def _(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """
    Вспомогательная функция для получения локализованных сообщений

    Args:
        key (str): Ключ сообщения
        lang (str): Код языка пользователя

    Returns:
        str: Локализованное сообщение
    """
    from bot.middlewares.i18n import I18nMiddleware

    # Базовые сообщения для разных языков
    messages = {
        'welcome_new': {
            'ru': "Добро пожаловать в SE1DHE Bot! 🤖\n\nЯ помогу вам выбрать и приобрести подходящего бота для ваших задач. Выберите действие из меню ниже:",
            'uk': "Ласкаво просимо до SE1DHE Bot! 🤖\n\nЯ допоможу вам вибрати та придбати відповідного бота для ваших завдань. Виберіть дію з меню нижче:",
            'en': "Welcome to SE1DHE Bot! 🤖\n\nI'll help you choose and purchase a suitable bot for your tasks. Select an action from the menu below:"
        },
        'welcome_back': {
            'ru': "С возвращением! 🤖\n\nРад видеть вас снова. Выберите действие из меню ниже:",
            'uk': "З поверненням! 🤖\n\nРадий бачити вас знову. Виберіть дію з меню нижче:",
            'en': "Welcome back! 🤖\n\nGlad to see you again. Select an action from the menu below:"
        }
    }

    # Если язык не поддерживается, используем русский
    if lang not in ['ru', 'uk', 'en']:
        lang = 'ru'

    # Возвращаем сообщение для указанного языка или русское сообщение, если ключ не найден
    return messages.get(key, {}).get(lang, messages.get(key, {}).get('ru', f"Message not found: {key}"))


def register_start_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики команды /start

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    dp.message.register(cmd_start, Command("start"))