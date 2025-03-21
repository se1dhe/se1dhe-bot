# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text

from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from models.user_language import UserLanguage
import logging

logger = logging.getLogger(__name__)

# Инициализируем хранилище языков пользователей
user_languages = UserLanguage()


async def cmd_settings(message: types.Message):
    """
    Обработчик команды /settings
    Показывает меню настроек
    """
    language = message.from_user.language_code or DEFAULT_LANGUAGE
    await show_settings_menu(message, language)


async def show_settings_menu(message: types.Message, language: str):
    """
    Показывает меню настроек
    """
    # Формируем клавиатуру
    keyboard = InlineKeyboardMarkup(row_width=1)

    # Кнопка выбора языка
    keyboard.add(InlineKeyboardButton(
        text=get_localized_text('settings_language', language),
        callback_data="settings:language"
    ))

    # Кнопка возврата в главное меню
    keyboard.add(InlineKeyboardButton(
        text=get_localized_text('back', language) + " ◀️",
        callback_data="menu:main"
    ))

    # Отправляем сообщение
    await message.answer(
        get_localized_text('settings_title', language) + "\n\n" +
        get_localized_text('settings_description', language),
        reply_markup=keyboard
    )


async def process_settings_callback(callback: types.CallbackQuery):
    """
    Обработчик callback-запросов для настроек
    """
    # Получаем действие из callback_data
    action = callback.data.split(':')[1]
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback.answer()

    # Обрабатываем соответствующее действие
    if action == 'language':
        await show_language_selection(callback, language)
    elif action in SUPPORTED_LANGUAGES:
        await set_language(callback, action)


async def show_language_selection(callback: types.CallbackQuery, language: str):
    """
    Показывает меню выбора языка
    """
    # Формируем клавиатуру
    keyboard = InlineKeyboardMarkup(row_width=1)

    # Добавляем кнопки для каждого поддерживаемого языка
    language_names = {
        'ru': '🇷🇺 Русский',
        'uk': '🇺🇦 Українська',
        'en': '🇬🇧 English'
    }

    for lang_code in SUPPORTED_LANGUAGES:
        # Помечаем текущий язык
        marker = "✅ " if lang_code == language else ""
        keyboard.add(InlineKeyboardButton(
            text=marker + language_names.get(lang_code, lang_code),
            callback_data=f"settings:{lang_code}"
        ))

    # Кнопка назад
    keyboard.add(InlineKeyboardButton(
        text=get_localized_text('back', language) + " ◀️",
        callback_data="settings:main"
    ))

    # Отправляем сообщение
    await callback.message.edit_text(
        get_localized_text('settings_language_title', language),
        reply_markup=keyboard
    )


async def set_language(callback: types.CallbackQuery, new_language: str):
    """
    Устанавливает новый язык для пользователя
    """
    user_id = callback.from_user.id

    # Сохраняем язык
    user_languages.set_language(user_id, new_language)

    # Получаем локализованное сообщение на новом языке
    confirmation_text = get_localized_text('settings_language_set', new_language)

    # Отправляем подтверждение
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('back', new_language) + " ◀️",
                    callback_data="settings:main"
                )]
            ]
        )
    )


def get_localized_text(key: str, lang: str) -> str:
    """
    Заглушка для получения локализованного текста
    В реальном приложении здесь бы использовалась I18n middleware

    Args:
        key (str): Ключ текста
        lang (str): Код языка

    Returns:
        str: Локализованный текст
    """
    # Базовые тексты для настроек
    texts = {
        'settings_title': {
            'ru': '⚙️ Настройки',
            'uk': '⚙️ Налаштування',
            'en': '⚙️ Settings'
        },
        'settings_description': {
            'ru': 'Здесь вы можете настроить параметры бота:',
            'uk': 'Тут ви можете налаштувати параметри бота:',
            'en': 'Here you can configure bot settings:'
        },
        'settings_language': {
            'ru': '🌐 Изменить язык',
            'uk': '🌐 Змінити мову',
            'en': '🌐 Change language'
        },
        'settings_language_title': {
            'ru': 'Выберите язык:',
            'uk': 'Виберіть мову:',
            'en': 'Select language:'
        },
        'settings_language_set': {
            'ru': '✅ Язык успешно изменен на Русский',
            'uk': '✅ Мову успішно змінено на Українську',
            'en': '✅ Language successfully changed to English'
        },
        'back': {
            'ru': 'Назад',
            'uk': 'Назад',
            'en': 'Back'
        }
    }

    # Если язык не поддерживается, используем русский
    if lang not in ['ru', 'uk', 'en']:
        lang = 'ru'

    return texts.get(key, {}).get(lang, f"Missing text: {key}")


def register_settings_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики для настроек

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Команда /settings
    dp.message.register(cmd_settings, Command("settings"))

    # Обработчик callback-запросов
    dp.callback_query.register(process_settings_callback,
                              lambda query: query.data.startswith("settings:"))