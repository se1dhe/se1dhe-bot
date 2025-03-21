# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text
from models.models import User, Order, Bot, OrderStatus
from database.db import Session as DbSession
from config.settings import DEFAULT_LANGUAGE

import logging

logger = logging.getLogger(__name__)


async def process_payment_callback(callback: types.CallbackQuery):
    """
    Обработчик callback-запросов для платежей
    """
    # Получаем действие из callback_data
    payment_system = callback.data.split(':')[1]
    user_id = callback.from_user.id
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback.answer()

    # Обрабатываем выбор платежной системы
    if payment_system == 'freekassa':
        await process_freekassa_payment(callback, user_id, language)
    elif payment_system == 'paykassa':
        await process_paykassa_payment(callback, user_id, language)


async def process_freekassa_payment(callback: types.CallbackQuery, user_id: int, language: str):
    """
    Обрабатывает оплату через FreeKassa
    """
    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.message.answer(
                get_localized_text('error_user_not_found', language)
            )
            return

        # Получаем корзину пользователя и создаем заказы
        # Здесь должна быть логика получения корзины и создания заказов
        # Это заглушка, которая просто уведомляет пользователя
        await callback.message.answer(
            get_localized_text('payment_processing', language) + "\n\n" +
            get_localized_text('payment_freekassa_redirect', language),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text('payment_open_link', language),
                        url="https://freekassa.ru"  # Заглушка URL
                    )],
                    [InlineKeyboardButton(
                        text=get_localized_text('cancel', language),
                        callback_data="payment:cancel"
                    )]
                ]
            )
        )

    except Exception as e:
        logger.error(f"Error processing FreeKassa payment: {e}")
        await callback.message.answer(get_localized_text('error_payment', language))
    finally:
        db.close()


async def process_paykassa_payment(callback: types.CallbackQuery, user_id: int, language: str):
    """
    Обрабатывает оплату через PayKassa
    """
    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.message.answer(
                get_localized_text('error_user_not_found', language)
            )
            return

        # Получаем корзину пользователя и создаем заказы
        # Здесь должна быть логика получения корзины и создания заказов
        # Это заглушка, которая просто уведомляет пользователя
        await callback.message.answer(
            get_localized_text('payment_processing', language) + "\n\n" +
            get_localized_text('payment_paykassa_redirect', language),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text('payment_open_link', language),
                        url="https://paykassa.pro"  # Заглушка URL
                    )],
                    [InlineKeyboardButton(
                        text=get_localized_text('cancel', language),
                        callback_data="payment:cancel"
                    )]
                ]
            )
        )

    except Exception as e:
        logger.error(f"Error processing PayKassa payment: {e}")
        await callback.message.answer(get_localized_text('error_payment', language))
    finally:
        db.close()


async def process_payment_cancel(callback: types.CallbackQuery):
    """
    Обрабатывает отмену платежа
    """
    language = callback.from_user.language_code or DEFAULT_LANGUAGE
    await callback.answer()
    await callback.message.answer(
        get_localized_text('payment_cancelled', language),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('back_to_cart', language),
                    callback_data="menu:cart"
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
    # Базовые тексты для платежей
    texts = {
        'payment_processing': {
            'ru': '⏳ Обработка платежа...',
            'uk': '⏳ Обробка платежу...',
            'en': '⏳ Processing payment...'
        },
        'payment_freekassa_redirect': {
            'ru': 'Сейчас вы будете перенаправлены на сайт FreeKassa для совершения оплаты.',
            'uk': 'Зараз вас буде перенаправлено на сайт FreeKassa для здійснення оплати.',
            'en': 'You will now be redirected to the FreeKassa website to make a payment.'
        },
        'payment_paykassa_redirect': {
            'ru': 'Сейчас вы будете перенаправлены на сайт PayKassa для совершения оплаты.',
            'uk': 'Зараз вас буде перенаправлено на сайт PayKassa для здійснення оплати.',
            'en': 'You will now be redirected to the PayKassa website to make a payment.'
        },
        'payment_open_link': {
            'ru': '🔗 Открыть ссылку для оплаты',
            'uk': '🔗 Відкрити посилання для оплати',
            'en': '🔗 Open payment link'
        },
        'payment_cancelled': {
            'ru': '❌ Платеж отменен',
            'uk': '❌ Платіж скасовано',
            'en': '❌ Payment cancelled'
        },
        'back_to_cart': {
            'ru': '🛍 Вернуться в корзину',
            'uk': '🛍 Повернутися до кошика',
            'en': '🛍 Back to cart'
        },
        'error_user_not_found': {
            'ru': 'Ошибка: пользователь не найден. Пожалуйста, перезапустите бота командой /start.',
            'uk': 'Помилка: користувача не знайдено. Будь ласка, перезапустіть бота командою /start.',
            'en': 'Error: user not found. Please restart the bot with the /start command.'
        },
        'error_payment': {
            'ru': 'Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже или обратитесь в поддержку.',
            'uk': 'Сталася помилка при створенні платежу. Будь ласка, спробуйте пізніше або зверніться до підтримки.',
            'en': 'An error occurred while creating the payment. Please try again later or contact support.'
        },
        'cancel': {
            'ru': 'Отмена',
            'uk': 'Скасувати',
            'en': 'Cancel'
        }
    }

    # Если язык не поддерживается, используем русский
    if lang not in ['ru', 'uk', 'en']:
        lang = 'ru'

    return texts.get(key, {}).get(lang, f"Missing text: {key}")


def register_payment_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики для платежей

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Обработчики callback-запросов
    dp.callback_query.register(process_payment_callback,
                              lambda query: query.data.startswith("payment:") and query.data != "payment:cancel")
    dp.callback_query.register(process_payment_cancel,
                              lambda query: query.data == "payment:cancel")