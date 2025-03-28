# -*- coding: utf-8 -*-
from aiogram import Dispatcher

from bot.handlers.payments import register_payment_handlers
from bot.handlers.start import register_start_handlers
from bot.handlers.help import register_help_handlers
from bot.handlers.menu import register_menu_handlers
from bot.handlers.catalog import register_catalog_handlers
from bot.handlers.cart import register_cart_handlers
from bot.handlers.settings import register_settings_handlers
from bot.handlers.support import register_support_handlers
from bot.handlers.reviews import register_reviews_handlers


def register_all_handlers(dp: Dispatcher):
    """
    Регистрирует все обработчики команд бота.

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    handlers = [
        register_start_handlers,
        register_help_handlers,
        register_menu_handlers,
        register_catalog_handlers,
        register_cart_handlers,
        register_settings_handlers,
        register_payment_handlers,
        register_support_handlers,
        register_reviews_handlers
    ]

    for handler in handlers:
        handler(dp)

    # Регистрируем обработчики сообщений
    from bot.handlers.support import process_user_message, process_user_photo, process_user_video, process_user_audio, \
        process_user_document

    dp.message.register(process_user_photo, lambda message: message.photo)
    dp.message.register(process_user_video, lambda message: message.video)
    dp.message.register(process_user_audio, lambda message: message.audio or message.voice)
    dp.message.register(process_user_document, lambda message: message.document)
    dp.message.register(process_user_message, lambda message: message.text and not message.text.startswith('/'))