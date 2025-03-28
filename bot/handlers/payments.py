# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text
from models.models import User, Order, Bot, OrderStatus, Cart
from database.db import Session as DbSession
from config.settings import DEFAULT_LANGUAGE
from payments.freekassa import FreeKassa
from payments.paykassa import PayKassa
from typing import Dict

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

        # Получаем корзину пользователя
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
        if not cart or not cart.items:
            await callback.message.answer(
                get_localized_text('cart_empty', language)
            )
            return

        # Рассчитываем общую сумму заказа
        total_amount = 0
        for item in cart.items:
            price = item.bot.price
            if item.bot.discount > 0:
                price = price * (1 - item.bot.discount / 100)
            total_amount += price * item.quantity

        # Создаем новый заказ для первого товара в корзине
        # (в реальной системе можно создать один заказ на все товары)
        first_item = cart.items[0]
        new_order = Order(
            user_id=user.id,
            bot_id=first_item.bot_id,
            amount=total_amount,
            status=OrderStatus.PENDING,
            payment_system="freekassa"
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Инициализируем FreeKassa
        freekassa = FreeKassa()

        # Генерируем ссылку на оплату
        payment_url = freekassa.generate_payment_link(
            order_id=new_order.id,
            amount=total_amount,
            description=f"Оплата заказа #{new_order.id}",
            email=None  # При необходимости можно добавить email пользователя
        )

        # Отправляем сообщение с ссылкой на оплату
        await callback.message.answer(
            get_localized_text('payment_processing', language) + "\n\n" +
            get_localized_text('payment_freekassa_redirect', language),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text('payment_open_link', language),
                        url=payment_url
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

        # Получаем корзину пользователя
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
        if not cart or not cart.items:
            await callback.message.answer(
                get_localized_text('cart_empty', language)
            )
            return

        # Рассчитываем общую сумму заказа
        total_amount = 0
        for item in cart.items:
            price = item.bot.price
            if item.bot.discount > 0:
                price = price * (1 - item.bot.discount / 100)
            total_amount += price * item.quantity

        # Создаем новый заказ для первого товара в корзине
        first_item = cart.items[0]
        new_order = Order(
            user_id=user.id,
            bot_id=first_item.bot_id,
            amount=total_amount,
            status=OrderStatus.PENDING,
            payment_system="paykassa"
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Инициализируем PayKassa
        paykassa = PayKassa()

        # Создаем платеж
        payment_data = paykassa.create_payment(
            order_id=new_order.id,
            amount=total_amount,
            description=f"Оплата заказа #{new_order.id}"
        )

        if not payment_data.get('success'):
            await callback.message.answer(
                get_localized_text('error_payment', language)
            )
            return

        # Отправляем сообщение с ссылкой на оплату
        await callback.message.answer(
            get_localized_text('payment_processing', language) + "\n\n" +
            get_localized_text('payment_paykassa_redirect', language),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text('payment_open_link', language),
                        url=payment_data['payment_url']
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


async def process_payment_notification(data: Dict, payment_system: str):
    """
    Обрабатывает уведомления о платежах от платежных систем.
    Этот метод должен быть вызван из FastAPI-обработчика вебхуков.
    """
    try:
        if payment_system == 'freekassa':
            # Инициализация FreeKassa
            freekassa = FreeKassa()

            # Проверка подписи
            if not freekassa.verify_notification(data):
                logger.warning("Invalid FreeKassa notification signature")
                return {"success": False}

            # Получение данных заказа
            order_id = int(data.get('MERCHANT_ORDER_ID'))
            amount = float(data.get('AMOUNT'))

            # Обновление статуса заказа
            db = DbSession()
            try:
                order = db.query(Order).filter(Order.id == order_id).first()
                if not order:
                    logger.warning(f"Order {order_id} not found")
                    return {"success": False}

                order.status = OrderStatus.PAID
                order.payment_system = "freekassa"
                order.payment_id = data.get('intid')
                db.commit()

                # Уведомление пользователя через Telegram-бота
                await send_payment_notification(order)

                return {"success": True}
            finally:
                db.close()

        elif payment_system == 'paykassa':
            # Инициализация PayKassa
            paykassa = PayKassa()

            # Проверка подписи
            if not paykassa.verify_notification(data):
                logger.warning("Invalid PayKassa notification signature")
                return {"success": False}

            # Получение данных заказа
            order_id = int(data.get('order_id'))
            amount = float(data.get('amount'))

            # Обновление статуса заказа
            db = DbSession()
            try:
                order = db.query(Order).filter(Order.id == order_id).first()
                if not order:
                    logger.warning(f"Order {order_id} not found")
                    return {"success": False}

                order.status = OrderStatus.PAID
                order.payment_system = "paykassa"
                order.payment_id = data.get('transaction_id')
                db.commit()

                # Уведомление пользователя через Telegram-бота
                await send_payment_notification(order)

                return {"success": True}
            finally:
                db.close()
        else:
            logger.warning(f"Unknown payment system: {payment_system}")
            return {"success": False}
    except Exception as e:
        logger.error(f"Error processing payment notification: {e}")
        return {"success": False}


async def send_payment_notification(order: Order):
    """Отправляет уведомление пользователю о успешной оплате заказа"""
    try:
        # Получаем данные пользователя и бота
        db = DbSession()
        try:
            user = db.query(User).filter(User.id == order.user_id).first()
            bot_item = db.query(Bot).filter(Bot.id == order.bot_id).first()

            if not user or not bot_item:
                logger.warning(f"User or bot not found for order {order.id}")
                return

            # Определяем язык пользователя
            language = user.language or DEFAULT_LANGUAGE

            # Создаем текст сообщения
            message_text = get_localized_text('payment_success', language) + "\n\n"
            message_text += f"**{bot_item.name}**\n"
            message_text += f"{get_localized_text('order_id', language)}: {order.id}\n"
            message_text += f"{get_localized_text('amount', language)}: {order.amount} руб.\n\n"

            # Создаем клавиатуру с кнопками
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text('download_bot', language),
                        url=f"/download/{bot_item.archive_path}" if bot_item.archive_path else "#"
                    )],
                    [InlineKeyboardButton(
                        text=get_localized_text('read_manual', language),
                        url=bot_item.readme_url or "#"
                    )]
                ]
            )

            # Добавляем кнопку для группы поддержки, если она указана
            if bot_item.support_group_link:
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=get_localized_text('join_support_group', language),
                        url=bot_item.support_group_link
                    )
                ])

            # Отправляем сообщение через бота
            # Предполагается, что бот уже инициализирован и доступен
            from bot.main import bot
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            logger.info(f"Payment notification sent to user {user.telegram_id} for order {order.id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error sending payment notification: {e}")


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
        'payment_success': {
            'ru': '✅ Оплата успешно прошла! Спасибо за покупку.',
            'uk': '✅ Оплата успішно пройшла! Дякуємо за покупку.',
            'en': '✅ Payment successful! Thank you for your purchase.'
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
        },
        'cart_empty': {
            'ru': 'Ваша корзина пуста. Перейдите в каталог, чтобы выбрать бота.',
            'uk': 'Ваш кошик порожній. Перейдіть до каталогу, щоб вибрати бота.',
            'en': 'Your cart is empty. Go to the catalog to choose a bot.'
        },
        'download_bot': {
            'ru': '📥 Скачать бота',
            'uk': '📥 Завантажити бота',
            'en': '📥 Download Bot'
        },
        'read_manual': {
            'ru': '📖 Прочитать инструкцию',
            'uk': '📖 Прочитати інструкцію',
            'en': '📖 Read Manual'
        },
        'join_support_group': {
            'ru': '👥 Присоединиться к группе поддержки',
            'uk': '👥 Приєднатися до групи підтримки',
            'en': '👥 Join Support Group'
        },
        'order_id': {
            'ru': 'Номер заказа',
            'uk': 'Номер замовлення',
            'en': 'Order ID'
        },
        'amount': {
            'ru': 'Сумма',
            'uk': 'Сума',
            'en': 'Amount'
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