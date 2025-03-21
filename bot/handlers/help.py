# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.filters import Command
from config.settings import DEFAULT_LANGUAGE
import logging

logger = logging.getLogger(__name__)


async def cmd_help(message: types.Message):
    """
    Обработчик команды /help
    Отправляет пользователю справочную информацию о боте
    """
    # Получаем язык пользователя
    language = message.from_user.language_code or DEFAULT_LANGUAGE

    # Отправляем справочное сообщение
    await message.answer(_get_help_text(language))


def _get_help_text(lang: str) -> str:
    """
    Возвращает локализованный текст справки

    Args:
        lang (str): Код языка пользователя

    Returns:
        str: Текст справки
    """
    # Если язык не поддерживается, используем русский
    if lang not in ['ru', 'uk', 'en']:
        lang = 'ru'

    help_texts = {
        'ru': """
📌 <b>Помощь по использованию SE1DHE Bot</b>

Этот бот поможет вам выбрать и приобрести подходящего Telegram-бота для ваших задач.

<b>Основные команды:</b>
• /start - запустить бота
• /help - показать это сообщение
• /catalog - перейти к каталогу ботов
• /cart - перейти к корзине
• /settings - настройки

<b>Как пользоваться:</b>
1. Выберите бота из каталога
2. Добавьте его в корзину
3. Перейдите к оформлению заказа
4. Выберите способ оплаты и оплатите
5. Получите доступ к боту!

<b>Поддержка:</b>
Если у вас возникли вопросы, используйте команду /support для связи с администрацией.
""",
        'uk': """
📌 <b>Допомога по використанню SE1DHE Bot</b>

Цей бот допоможе вам вибрати та придбати відповідного Telegram-бота для ваших завдань.

<b>Основні команди:</b>
• /start - запустити бота
• /help - показати це повідомлення
• /catalog - перейти до каталогу ботів
• /cart - перейти до кошика
• /settings - налаштування

<b>Як користуватися:</b>
1. Виберіть бота з каталогу
2. Додайте його до кошика
3. Перейдіть до оформлення замовлення
4. Виберіть спосіб оплати та оплатіть
5. Отримайте доступ до бота!

<b>Підтримка:</b>
Якщо у вас виникли питання, використовуйте команду /support для зв'язку з адміністрацією.
""",
        'en': """
📌 <b>SE1DHE Bot Usage Help</b>

This bot will help you choose and purchase a suitable Telegram bot for your tasks.

<b>Main commands:</b>
• /start - start the bot
• /help - show this message
• /catalog - go to the bot catalog
• /cart - go to your cart
• /settings - settings

<b>How to use:</b>
1. Choose a bot from the catalog
2. Add it to your cart
3. Proceed to checkout
4. Choose a payment method and pay
5. Get access to the bot!

<b>Support:</b>
If you have any questions, use the /support command to contact the administration.
"""
    }

    return help_texts.get(lang, help_texts['ru'])


def register_help_handlers(dp: Dispatcher):
    """
    Регистрирует обработчик команды /help

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    dp.message.register(cmd_help, Command("help"))