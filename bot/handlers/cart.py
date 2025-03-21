# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text
from sqlalchemy.orm import Session
from models.models import Bot, Cart, CartItem, User
from database.db import Session as DbSession
from config.settings import DEFAULT_LANGUAGE
from typing import Dict, List, Optional
import logging


logger = logging.getLogger(__name__)


async def cmd_cart(message: types.Message):
    """
    Обработчик команды /cart
    Показывает содержимое корзины пользователя
    """
    await show_cart(message)


async def show_cart(message: types.Message):
    """
    Показывает содержимое корзины пользователя
    """
    user_id = message.from_user.id
    language = message.from_user.language_code or DEFAULT_LANGUAGE

    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            await message.answer("Пользователь не найден. Пожалуйста, запустите бота командой /start")
            return

        # Получаем корзину пользователя
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()

        # Если корзины нет или она пуста
        if not cart or not cart.items:
            await message.answer(
                get_localized_text('cart_title', language) + "\n\n" +
                get_localized_text('cart_empty', language),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=get_localized_text('catalog', language),
                            callback_data="menu:catalog"
                        )]
                    ]
                )
            )
            return

        # Формируем текст с содержимым корзины
        cart_text = get_localized_text('cart_title', language) + "\n\n"
        cart_text += get_localized_text('cart_description', language) + "\n\n"

        total_price = 0

        # Формируем клавиатуру
        keyboard = InlineKeyboardMarkup(row_width=2)

        # Добавляем информацию о каждом боте в корзине
        for item in cart.items:
            bot = item.bot

            # Вычисляем цену с учетом скидки
            price = bot.price
            if bot.discount > 0:
                price = price * (1 - bot.discount / 100)

            item_total = price * item.quantity
            total_price += item_total

            # Информация о боте
            cart_text += f"• {bot.name} x{item.quantity} - {item_total:.2f} руб.\n"

            # Кнопки управления количеством
            keyboard.add(
                InlineKeyboardButton(
                    text=f"❌ {bot.name}",
                    callback_data=f"cart:remove:{bot.id}"
                )
            )

        # Добавляем итоговую стоимость
        cart_text += "\n" + get_localized_text('cart_total', language).format(total=total_price)

        # Добавляем кнопки
        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('cart_checkout', language),
            callback_data="cart:checkout"
        ))

        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('cart_clear', language),
            callback_data="cart:clear"
        ))

        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('back', language) + " ◀️",
            callback_data="menu:main"
        ))

        # Отправляем сообщение
        await message.answer(cart_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error showing cart: {e}")
        await message.answer("Произошла ошибка при загрузке корзины. Пожалуйста, попробуйте позже.")
    finally:
        db.close()


async def process_cart_callback(callback: types.CallbackQuery):
    """
    Обработчик callback-запросов для корзины
    """
    # Получаем действие из callback_data
    action = callback.data.split(':')[1]

    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback.answer()

    # Обрабатываем соответствующее действие
    if action == 'add':
        await add_to_cart(callback)
    elif action == 'remove':
        await remove_from_cart(callback)
    elif action == 'clear':
        await clear_cart(callback)
    elif action == 'checkout':
        await checkout(callback)
    elif action == 'buy_now':
        await buy_now(callback)


async def add_to_cart(callback: types.CallbackQuery):
    """
    Добавляет бота в корзину
    """
    # Получаем ID бота из callback_data
    bot_id = int(callback.data.split(':')[2])
    user_id = callback.from_user.id
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            await callback.message.answer("Пользователь не найден. Пожалуйста, запустите бота командой /start")
            return

        # Получаем информацию о боте
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            await callback.message.answer("Бот не найден. Возможно, он был удален.")
            return

        # Получаем или создаем корзину
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()

        if not cart:
            cart = Cart(user_id=user.id)
            db.add(cart)
            db.commit()
            db.refresh(cart)

        # Проверяем, есть ли уже этот бот в корзине
        cart_item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.bot_id == bot_id
        ).first()

        if cart_item:
            # Если бот уже в корзине, увеличиваем количество
            cart_item.quantity += 1
        else:
            # Иначе добавляем новый элемент
            cart_item = CartItem(
                cart_id=cart.id,
                bot_id=bot_id,
                quantity=1
            )
            db.add(cart_item)

        db.commit()

        # Отправляем сообщение об успешном добавлении
        message_text = get_localized_text('bot_added_to_cart', language).format(name=bot.name)

        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('cart_title', language),
                    callback_data="menu:cart"
                )],
                [InlineKeyboardButton(
                    text=get_localized_text('back', language) + " ◀️",
                    callback_data="bot:" + str(bot_id)
                )]
            ]
        )

        await callback.message.answer(message_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        await callback.message.answer("Произошла ошибка при добавлении в корзину. Пожалуйста, попробуйте позже.")
    finally:
        db.close()


async def remove_from_cart(callback: types.CallbackQuery):
    """
    Удаляет бота из корзины
    """
    # Получаем ID бота из callback_data
    bot_id = int(callback.data.split(':')[2])
    user_id = callback.from_user.id
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            await callback.message.answer("Пользователь не найден. Пожалуйста, запустите бота командой /start")
            return

        # Получаем корзину
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()

        if not cart:
            await callback.message.answer("Корзина пуста.")
            return

        # Получаем информацию о боте
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            await callback.message.answer("Бот не найден. Возможно, он был удален.")
            return

        # Удаляем элемент из корзины
        db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.bot_id == bot_id
        ).delete()

        db.commit()

        # Отправляем сообщение об успешном удалении
        message_text = get_localized_text('bot_removed_from_cart', language).format(name=bot.name)

        # Обновляем корзину
        await callback.message.answer(message_text)
        await show_cart_callback(callback)

    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        await callback.message.answer("Произошла ошибка при удалении из корзины. Пожалуйста, попробуйте позже.")
    finally:
        db.close()


async def clear_cart(callback: types.CallbackQuery):
    """
    Очищает корзину пользователя
    """
    user_id = callback.from_user.id
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            await callback.message.answer("Пользователь не найден. Пожалуйста, запустите бота командой /start")
            return

        # Получаем корзину
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()

        if not cart:
            await callback.message.answer("Корзина уже пуста.")
            return

        # Удаляем все элементы из корзины
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()

        # Отправляем сообщение об успешной очистке
        await callback.message.answer("Корзина очищена.")

        # Показываем пустую корзину
        await callback.message.answer(
            get_localized_text('cart_title', language) + "\n\n" +
            get_localized_text('cart_empty', language),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text('catalog', language),
                        callback_data="menu:catalog"
                    )]
                ]
            )
        )

    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        await callback.message.answer("Произошла ошибка при очистке корзины. Пожалуйста, попробуйте позже.")
    finally:
        db.close()


async def checkout(callback: types.CallbackQuery):
    """
    Переход к оформлению заказа
    """
    # Здесь будет переход к обработчику оформления заказа
    # Временная заглушка
    language = callback.from_user.language_code or DEFAULT_LANGUAGE
    await callback.message.answer(
        get_localized_text('checkout_title', language) + "\n\n" +
        get_localized_text('checkout_description', language),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="FreeKassa",
                    callback_data="payment:freekassa"
                )],
                [InlineKeyboardButton(
                    text="PayKassa",
                    callback_data="payment:paykassa"
                )],
                [InlineKeyboardButton(
                    text=get_localized_text('back', language) + " ◀️",
                    callback_data="menu:cart"
                )]
            ]
        )
    )


async def buy_now(callback: types.CallbackQuery):
    """
    Покупка бота сразу (добавление в корзину и переход к оформлению)
    """
    # Получаем ID бота из callback_data
    bot_id = int(callback.data.split(':')[2])

    # Добавляем бота в корзину
    # Создаем новый callback_data для добавления в корзину
    new_callback = callback
    new_callback.data = f"cart:add:{bot_id}"

    # Добавляем в корзину
    await add_to_cart(new_callback)

    # Переходим к оформлению заказа
    await checkout(callback)


async def show_cart_callback(callback: types.CallbackQuery):
    """
    Показывает содержимое корзины в ответ на callback-запрос
    """
    user_id = callback.from_user.id
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            await callback.message.answer("Пользователь не найден. Пожалуйста, запустите бота командой /start")
            return

        # Получаем корзину пользователя
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()

        # Если корзины нет или она пуста
        if not cart or not cart.items:
            await callback.message.edit_text(
                get_localized_text('cart_title', language) + "\n\n" +
                get_localized_text('cart_empty', language),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=get_localized_text('catalog', language),
                            callback_data="menu:catalog"
                        )]
                    ]
                )
            )
            return

        # Формируем текст с содержимым корзины
        cart_text = get_localized_text('cart_title', language) + "\n\n"
        cart_text += get_localized_text('cart_description', language) + "\n\n"

        total_price = 0

        # Формируем клавиатуру
        keyboard = InlineKeyboardMarkup(row_width=2)

        # Добавляем информацию о каждом боте в корзине
        for item in cart.items:
            bot = item.bot

            # Вычисляем цену с учетом скидки
            price = bot.price
            if bot.discount > 0:
                price = price * (1 - bot.discount / 100)

            item_total = price * item.quantity
            total_price += item_total

            # Информация о боте
            cart_text += f"• {bot.name} x{item.quantity} - {item_total:.2f} руб.\n"

            # Кнопки управления количеством
            keyboard.add(
                InlineKeyboardButton(
                    text=f"❌ {bot.name}",
                    callback_data=f"cart:remove:{bot.id}"
                )
            )

        # Добавляем итоговую стоимость
        cart_text += "\n" + get_localized_text('cart_total', language).format(total=total_price)

        # Добавляем кнопки
        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('cart_checkout', language),
            callback_data="cart:checkout"
        ))

        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('cart_clear', language),
            callback_data="cart:clear"
        ))

        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('back', language) + " ◀️",
            callback_data="menu:main"
        ))

        # Отправляем сообщение
        await callback.message.edit_text(cart_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error showing cart: {e}")
        await callback.message.answer("Произошла ошибка при загрузке корзины. Пожалуйста, попробуйте позже.")
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
    # Базовые тексты для корзины
    texts = {
        'cart_title': {
            'ru': '🛍 Корзина',
            'uk': '🛍 Кошик',
            'en': '🛍 Cart'
        },
        'cart_description': {
            'ru': 'Ваши выбранные боты:',
            'uk': 'Ваші вибрані боти:',
            'en': 'Your selected bots:'
        },
        'cart_empty': {
            'ru': 'Ваша корзина пуста. Перейдите в каталог, чтобы выбрать бота.',
            'uk': 'Ваш кошик порожній. Перейдіть до каталогу, щоб вибрати бота.',
            'en': 'Your cart is empty. Go to the catalog to choose a bot.'
        },
        'cart_total': {
            'ru': 'Итого: {total:.2f} руб.',
            'uk': 'Всього: {total:.2f} руб.',
            'en': 'Total: {total:.2f} RUB'
        },
        'cart_checkout': {
            'ru': '💳 Оформить заказ',
            'uk': '💳 Оформити замовлення',
            'en': '💳 Checkout'
        },
        'cart_clear': {
            'ru': '🗑 Очистить корзину',
            'uk': '🗑 Очистити кошик',
            'en': '🗑 Clear Cart'
        },
        'catalog': {
            'ru': '🛒 Перейти в каталог',
            'uk': '🛒 Перейти до каталогу',
            'en': '🛒 Go to Catalog'
        },
        'bot_added_to_cart': {
            'ru': '✅ Бот "{name}" добавлен в корзину!',
            'uk': '✅ Бот "{name}" додано до кошика!',
            'en': '✅ Bot "{name}" has been added to your cart!'
        },
        'bot_removed_from_cart': {
            'ru': '❌ Бот "{name}" удален из корзины.',
            'uk': '❌ Бот "{name}" видалено з кошика.',
            'en': '❌ Bot "{name}" has been removed from your cart.'
        },
        'checkout_title': {
            'ru': '🛒 Оформление заказа',
            'uk': '🛒 Оформлення замовлення',
            'en': '🛒 Checkout'
        },
        'checkout_description': {
            'ru': 'Выберите способ оплаты:',
            'uk': 'Виберіть спосіб оплати:',
            'en': 'Choose a payment method:'
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


def register_cart_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики для корзины

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Команда /cart
    dp.message.register(cmd_cart, Command("cart"))

    # Обработчики колбэков
    dp.callback_query.register(process_cart_callback,
                               lambda query: query.data.startswith("cart:"))