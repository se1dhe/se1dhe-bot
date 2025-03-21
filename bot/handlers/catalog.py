# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.formatting import Text

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from models.models import Bot, BotCategory
from database.db import Session as DbSession
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


async def cmd_catalog(message: types.Message):
    """
    Обработчик команды /catalog
    Показывает список категорий и ботов
    """
    await show_catalog_categories(message)


async def show_catalog_categories(message: types.Message):
    """
    Показывает список категорий ботов
    """
    # Получаем список категорий из базы данных
    db = DbSession()
    try:
        categories = db.query(BotCategory).all()

        # Формируем клавиатуру
        keyboard = InlineKeyboardMarkup(row_width=2)

        # Если категории есть, добавляем кнопки для них
        if categories:
            for category in categories:
                keyboard.add(InlineKeyboardButton(
                    text=category.name,
                    callback_data=f"category:{category.id}"
                ))

        # Добавляем кнопку для просмотра всех ботов
        keyboard.add(InlineKeyboardButton(
            text="Все боты",
            callback_data="category:all"
        ))

        # Добавляем кнопку возврата в главное меню
        keyboard.add(InlineKeyboardButton(
            text="◀️ Назад в меню",
            callback_data="menu:main"
        ))

        # Отправляем сообщение с категориями
        language = message.from_user.language_code
        await message.answer(
            get_localized_text('catalog_title', language) + "\n\n" +
            get_localized_text('catalog_description', language),
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error showing catalog categories: {e}")
        await message.answer("Произошла ошибка при загрузке каталога. Пожалуйста, попробуйте позже.")
    finally:
        db.close()


async def process_category_selection(callback: types.CallbackQuery):
    """
    Обработчик выбора категории
    """
    # Отвечаем на callback-запрос
    await callback.answer()

    # Получаем ID категории из callback_data
    category_id = callback.data.split(':')[1]

    if category_id == 'all':
        # Показываем все боты
        await show_bots_list(callback, None)
    else:
        # Показываем боты выбранной категории
        await show_bots_list(callback, int(category_id))


async def show_bots_list(callback: types.CallbackQuery, category_id: Optional[int]):
    """
    Показывает список ботов в выбранной категории

    Args:
        callback (types.CallbackQuery): Callback-запрос
        category_id (Optional[int]): ID категории или None для всех ботов
    """
    db = DbSession()
    try:
        # Формируем запрос
        if category_id:
            bots = db.query(Bot).filter(Bot.category_id == category_id).all()
            category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
            category_name = category.name if category else "Категория"
        else:
            bots = db.query(Bot).all()
            category_name = "Все боты"

        # Формируем клавиатуру
        keyboard = InlineKeyboardMarkup(row_width=1)

        # Если боты есть, добавляем кнопки для них
        if bots:
            for bot in bots:
                # Вычисляем фактическую цену с учетом скидки
                price = bot.price
                if bot.discount > 0:
                    price = bot.price * (1 - bot.discount / 100)

                # Добавляем информацию о скидке, если она есть
                discount_info = f" (-{bot.discount}%)" if bot.discount > 0 else ""

                keyboard.add(InlineKeyboardButton(
                    text=f"{bot.name} - {price:.2f} руб.{discount_info}",
                    callback_data=f"bot:{bot.id}"
                ))
        else:
            # Если ботов нет, показываем сообщение
            language = callback.from_user.language_code
            await callback.message.edit_text(
                get_localized_text('catalog_title', language) + "\n\n" +
                f"{category_name}: " + get_localized_text('catalog_empty', language),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="◀️ Назад к категориям",
                            callback_data="menu:catalog"
                        )]
                    ]
                )
            )
            return

        # Добавляем кнопку возврата к категориям
        keyboard.add(InlineKeyboardButton(
            text="◀️ Назад к категориям",
            callback_data="menu:catalog"
        ))

        # Отправляем сообщение со списком ботов
        language = callback.from_user.language_code
        await callback.message.edit_text(
            get_localized_text('catalog_title', language) + "\n\n" +
            f"{category_name}:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error showing bots list: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке списка ботов. Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ Назад к категориям",
                        callback_data="menu:catalog"
                    )]
                ]
            )
        )
    finally:
        db.close()


async def process_bot_selection(callback: types.CallbackQuery):
    """
    Обработчик выбора бота из списка
    """
    # Отвечаем на callback-запрос
    await callback.answer()

    # Получаем ID бота из callback_data
    bot_id = int(callback.data.split(':')[1])

    # Показываем детальную информацию о боте
    await show_bot_detail(callback, bot_id)


async def show_bot_detail(callback: types.CallbackQuery, bot_id: int):
    """
    Показывает детальную информацию о боте

    Args:
        callback (types.CallbackQuery): Callback-запрос
        bot_id (int): ID бота
    """
    db = DbSession()
    try:
        # Получаем информацию о боте
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            await callback.message.edit_text(
                "Бот не найден. Возможно, он был удален.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="◀️ Назад к каталогу",
                            callback_data="menu:catalog"
                        )]
                    ]
                )
            )
            return

        # Вычисляем фактическую цену с учетом скидки
        price = bot.price
        final_price = price
        if bot.discount > 0:
            final_price = price * (1 - bot.discount / 100)

        # Формируем информацию о скидке
        discount_text = ""
        if bot.discount > 0:
            language = callback.from_user.language_code
            discount_text = get_localized_text('bot_discount', language).format(discount=bot.discount)
            discount_text += f"\n💲 Цена со скидкой: {final_price:.2f} руб."

        # Формируем клавиатуру
        keyboard = InlineKeyboardMarkup(row_width=1)

        # Кнопка добавления в корзину
        keyboard.add(InlineKeyboardButton(
            text="🛒 Добавить в корзину",
            callback_data=f"cart:add:{bot_id}"
        ))

        # Кнопка покупки сразу
        keyboard.add(InlineKeyboardButton(
            text="💳 Купить сейчас",
            callback_data=f"cart:buy_now:{bot_id}"
        ))

        # Кнопка возврата к списку ботов
        keyboard.add(InlineKeyboardButton(
            text="◀️ Назад к списку",
            callback_data=f"category:{bot.category_id or 'all'}"
        ))

        # Отправляем сообщение с информацией о боте
        language = callback.from_user.language_code
        message_text = get_localized_text('bot_info', language).format(
            name=bot.name,
            description=bot.description,
            price=price,
            discount_text=discount_text
        )

        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error showing bot detail: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке информации о боте. Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ Назад к каталогу",
                        callback_data="menu:catalog"
                    )]
                ]
            )
        )
    finally:
        db.close()


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
    # Базовые тексты для каталога
    texts = {
        'catalog_title': {
            'ru': '🛒 Каталог ботов',
            'uk': '🛒 Каталог ботів',
            'en': '🛒 Bot Catalog'
        },
        'catalog_description': {
            'ru': 'Выберите категорию или конкретного бота:',
            'uk': 'Виберіть категорію або конкретного бота:',
            'en': 'Choose a category or a specific bot:'
        },
        'catalog_empty': {
            'ru': 'К сожалению, в данной категории пока нет ботов.',
            'uk': 'На жаль, в даній категорії поки немає ботів.',
            'en': 'Unfortunately, there are no bots in this category yet.'
        },
        'bot_info': {
            'ru': '📌 <b>{name}</b>\n\n{description}\n\n💰 Цена: {price:.2f} руб.\n{discount_text}',
            'uk': '📌 <b>{name}</b>\n\n{description}\n\n💰 Ціна: {price:.2f} руб.\n{discount_text}',
            'en': '📌 <b>{name}</b>\n\n{description}\n\n💰 Price: {price:.2f} RUB\n{discount_text}'
        },
        'bot_discount': {
            'ru': '🔥 Скидка: {discount}%',
            'uk': '🔥 Знижка: {discount}%',
            'en': '🔥 Discount: {discount}%'
        }
    }

    # Если язык не поддерживается, используем русский
    if lang not in ['ru', 'uk', 'en']:
        lang = 'ru'

    return texts.get(key, {}).get(lang, f"Missing text: {key}")


def register_catalog_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики для каталога

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Команда /catalog
    dp.message.register(cmd_catalog, Command("catalog"))

    # Обработчики колбэков
    dp.callback_query.register(process_category_selection,
                               lambda query: query.data.startswith("category:"))
    dp.callback_query.register(process_bot_selection,
                               lambda query: query.data.startswith("bot:"))