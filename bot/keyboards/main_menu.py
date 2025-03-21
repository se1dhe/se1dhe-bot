# -*- coding: utf-8 -*-
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import DEFAULT_LANGUAGE


def get_main_menu_keyboard(lang: str = DEFAULT_LANGUAGE) -> ReplyKeyboardMarkup:
    """
    Возвращает ReplyKeyboardMarkup с кнопками главного меню

    Args:
        lang (str): Код языка пользователя

    Returns:
        ReplyKeyboardMarkup: Клавиатура главного меню
    """
    # Локализация кнопок
    buttons = {
        'catalog': {
            'ru': '🛒 Каталог',
            'uk': '🛒 Каталог',
            'en': '🛒 Catalog'
        },
        'cart': {
            'ru': '🛍 Корзина',
            'uk': '🛍 Кошик',
            'en': '🛍 Cart'
        },
        'my_bots': {
            'ru': '🤖 Мои боты',
            'uk': '🤖 Мої боти',
            'en': '🤖 My bots'
        },
        'support': {
            'ru': '🆘 Поддержка',
            'uk': '🆘 Підтримка',
            'en': '🆘 Support'
        },
        'settings': {
            'ru': '⚙️ Настройки',
            'uk': '⚙️ Налаштування',
            'en': '⚙️ Settings'
        }
    }

    # Проверка языка
    if lang not in ['ru', 'uk', 'en']:
        lang = DEFAULT_LANGUAGE

    # Создаем клавиатуру
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=buttons['catalog'][lang]),
                KeyboardButton(text=buttons['cart'][lang])
            ],
            [
                KeyboardButton(text=buttons['my_bots'][lang]),
                KeyboardButton(text=buttons['support'][lang])
            ],
            [
                KeyboardButton(text=buttons['settings'][lang])
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )

    return keyboard


def get_inline_main_menu(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """
    Возвращает InlineKeyboardMarkup с кнопками главного меню

    Args:
        lang (str): Код языка пользователя

    Returns:
        InlineKeyboardMarkup: Инлайн-клавиатура главного меню
    """
    # Локализация кнопок
    buttons = {
        'catalog': {
            'ru': '🛒 Каталог',
            'uk': '🛒 Каталог',
            'en': '🛒 Catalog'
        },
        'cart': {
            'ru': '🛍 Корзина',
            'uk': '🛍 Кошик',
            'en': '🛍 Cart'
        },
        'my_bots': {
            'ru': '🤖 Мои боты',
            'uk': '🤖 Мої боти',
            'en': '🤖 My bots'
        },
        'support': {
            'ru': '🆘 Поддержка',
            'uk': '🆘 Підтримка',
            'en': '🆘 Support'
        },
        'settings': {
            'ru': '⚙️ Настройки',
            'uk': '⚙️ Налаштування',
            'en': '⚙️ Settings'
        }
    }

    # Проверка языка
    if lang not in ['ru', 'uk', 'en']:
        lang = DEFAULT_LANGUAGE

    # Создаем инлайн клавиатуру
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=buttons['catalog'][lang], callback_data="menu:catalog"),
                InlineKeyboardButton(text=buttons['cart'][lang], callback_data="menu:cart")
            ],
            [
                InlineKeyboardButton(text=buttons['my_bots'][lang], callback_data="menu:my_bots"),
                InlineKeyboardButton(text=buttons['support'][lang], callback_data="menu:support")
            ],
            [
                InlineKeyboardButton(text=buttons['settings'][lang], callback_data="menu:settings")
            ]
        ]
    )

    return keyboard