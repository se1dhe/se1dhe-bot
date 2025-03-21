# -*- coding: utf-8 -*-
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import BOT_TOKEN
from bot.middlewares.i18n import I18nMiddleware
from bot.handlers import register_all_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация middleware
i18n = I18nMiddleware(bot_dir="bot")
dp.message.middleware(i18n)
dp.callback_query.middleware(i18n)


async def main():
    # Регистрация всех хэндлеров
    register_all_handlers(dp)

    # Запуск бота
    logging.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")