# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.utils.formatting import Text

from bot.keyboards.main_menu import get_main_menu_keyboard, get_inline_main_menu
from config.settings import DEFAULT_LANGUAGE
import logging

logger = logging.getLogger(__name__)

# Словарь с локализованными текстами для кнопок меню
menu_texts = {
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


# Обработчики текстовых команд меню
async def process_catalog_command(message: types.Message):
    """Обработчик кнопки Каталог"""
    lang = message.from_user.language_code or DEFAULT_LANGUAGE
    await message.answer(
        get_localized_text('catalog_header', lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    # Здесь будет вызов функции показа каталога ботов


async def process_cart_command(message: types.Message):
    """Обработчик кнопки Корзина"""
    lang = message.from_user.language_code or DEFAULT_LANGUAGE
    await message.answer(
        get_localized_text('cart_header', lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    # Здесь будет вызов функции показа корзины


async def process_my_bots_command(message: types.Message):
    """Обработчик кнопки Мои боты"""
    lang = message.from_user.language_code or DEFAULT_LANGUAGE
    await message.answer(
        get_localized_text('my_bots_header', lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    # Здесь будет вызов функции показа приобретенных ботов


async def process_support_command(message: types.Message):
    """Обработчик кнопки Поддержка"""
    lang = message.from_user.language_code or DEFAULT_LANGUAGE
    await message.answer(
        get_localized_text('support_header', lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    # Здесь будет вызов функции отправки запроса в поддержку


async def process_settings_command(message: types.Message):
    """Обработчик кнопки Настройки"""
    lang = message.from_user.language_code or DEFAULT_LANGUAGE
    await message.answer(
        get_localized_text('settings_header', lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    # Здесь будет вызов функции настроек


# Обработчики inline-кнопок меню
async def process_menu_callback(callback: types.CallbackQuery):
    """Обработчик callback-запросов от inline-кнопок меню"""
    lang = callback.from_user.language_code or DEFAULT_LANGUAGE
    action = callback.data.split(':')[1]

    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback.answer()

    # Обрабатываем соответствующее действие
    if action == 'catalog':
        await callback.message.answer(
            get_localized_text('catalog_header', lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    elif action == 'cart':
        await callback.message.answer(
            get_localized_text('cart_header', lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    elif action == 'my_bots':
        await callback.message.answer(
            get_localized_text('my_bots_header', lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    elif action == 'support':
        await callback.message.answer(
            get_localized_text('support_header', lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    elif action == 'settings':
        await callback.message.answer(
            get_localized_text('settings_header', lang),
            reply_markup=get_main_menu_keyboard(lang)
        )


def get_localized_text(key: str, lang: str) -> str:
    """
    Возвращает локализованный текст по ключу

    Args:
        key (str): Ключ текста
        lang (str): Код языка

    Returns:
        str: Локализованный текст
    """
    # Если язык не поддерживается, используем русский
    if lang not in ['ru', 'uk', 'en']:
        lang = 'ru'

    texts = {
        'catalog_header': {
            'ru': '🛒 <b>Каталог ботов</b>\n\nВыберите категорию или конкретного бота:',
            'uk': '🛒 <b>Каталог ботів</b>\n\nВиберіть категорію або конкретного бота:',
            'en': '🛒 <b>Bot Catalog</b>\n\nChoose a category or a specific bot:'
        },
        'cart_header': {
            'ru': '🛍 <b>Корзина</b>\n\nВаши выбранные боты:',
            'uk': '🛍 <b>Кошик</b>\n\nВаші вибрані боти:',
            'en': '🛍 <b>Cart</b>\n\nYour selected bots:'
        },
        'my_bots_header': {
            'ru': '🤖 <b>Мои боты</b>\n\nСписок приобретенных вами ботов:',
            'uk': '🤖 <b>Мої боти</b>\n\nСписок придбаних вами ботів:',
            'en': '🤖 <b>My Bots</b>\n\nList of bots you have purchased:'
        },
        'support_header': {
            'ru': '🆘 <b>Поддержка</b>\n\nЗадайте ваш вопрос или опишите проблему:',
            'uk': '🆘 <b>Підтримка</b>\n\nЗадайте ваше питання або опишіть проблему:',
            'en': '🆘 <b>Support</b>\n\nAsk your question or describe the problem:'
        },
        'settings_header': {
            'ru': '⚙️ <b>Настройки</b>\n\nВы можете изменить язык или другие параметры:',
            'uk': '⚙️ <b>Налаштування</b>\n\nВи можете змінити мову або інші параметри:',
            'en': '⚙️ <b>Settings</b>\n\nYou can change language or other settings:'
        }
    }

    return texts.get(key, {}).get(lang, f"Missing text: {key}")


def register_menu_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики команд меню

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Регистрация обработчиков текстовых кнопок
    for lang in ['ru', 'uk', 'en']:
        catalog_text = menu_texts['catalog'][lang]
        dp.message.register(
            process_catalog_command,
            lambda message, text=catalog_text: message.text == text
        )

        cart_text = menu_texts['cart'][lang]
        dp.message.register(
            process_cart_command,
            lambda message, text=cart_text: message.text == text
        )

        my_bots_text = menu_texts['my_bots'][lang]
        dp.message.register(
            process_my_bots_command,
            lambda message, text=my_bots_text: message.text == text
        )

        support_text = menu_texts['support'][lang]
        dp.message.register(
            process_support_command,
            lambda message, text=support_text: message.text == text
        )

        settings_text = menu_texts['settings'][lang]
        dp.message.register(
            process_settings_command,
            lambda message, text=settings_text: message.text == text
        )

    # Регистрация обработчиков inline-кнопок
    dp.callback_query.register(
        process_menu_callback,
        lambda query: query.data.startswith("menu:")
    )