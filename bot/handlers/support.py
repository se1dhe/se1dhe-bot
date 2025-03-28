# -*- coding: utf-8 -*-
import os
import uuid

from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text
from database.db import Session as DbSession


from config.settings import ADMIN_IDS, DEFAULT_LANGUAGE, MESSAGES_MEDIA_DIR
import logging

from models.models import Message, User

logger = logging.getLogger(__name__)


# Определяем состояния FSM
class SupportStates(StatesGroup):
    waiting_for_message = State()


async def cmd_support(message: types.Message, state: FSMContext):
    """
    Обработчик команды /support
    Начинает диалог с поддержкой
    """

    language = message.from_user.language_code or DEFAULT_LANGUAGE

    # Отправляем сообщение с инструкцией
    await message.answer(
        get_localized_text('support_title', language) + "\n\n" +
        get_localized_text('support_description', language),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('cancel', language),
                    callback_data="support:cancel"
                )]
            ]
        )
    )

    # Устанавливаем состояние "ожидание сообщения"
    await state.set_state(SupportStates.waiting_for_message)


async def process_support_message(message: types.Message, state: FSMContext):
    """
    Обрабатывает сообщение для поддержки
    """
    language = message.from_user.language_code or DEFAULT_LANGUAGE
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"
    user_fullname = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "N/A"

    # Текст сообщения
    support_text = message.text

    # Формируем сообщение для администраторов
    admin_message = (
        f"📩 Новое сообщение в поддержку\n\n"
        f"От: {user_fullname} (@{username})\n"
        f"ID: {user_id}\n\n"
        f"Сообщение:\n{support_text}"
    )

    # Отправляем сообщение всем администраторам
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="Ответить",
                            callback_data=f"support:reply:{user_id}"
                        )]
                    ]
                )
            )
        except Exception as e:
            logger.error(f"Error sending support message to admin {admin_id}: {e}")

    # Отвечаем пользователю, что сообщение отправлено
    await message.answer(
        get_localized_text('support_sent', language),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('back_to_menu', language),
                    callback_data="menu:main"
                )]
            ]
        )
    )

    # Сбрасываем состояние
    await state.clear()


async def cancel_support(callback: types.CallbackQuery, state: FSMContext):
    """
    Отменяет диалог с поддержкой
    """
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    # Отвечаем на callback
    await callback.answer()

    # Сбрасываем состояние
    await state.clear()

    # Отправляем сообщение об отмене
    await callback.message.answer(
        get_localized_text('support_cancelled', language),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('back_to_menu', language),
                    callback_data="menu:main"
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
    # Базовые тексты для поддержки
    texts = {
        'support_title': {
            'ru': '🆘 Поддержка',
            'uk': '🆘 Підтримка',
            'en': '🆘 Support'
        },
        'support_description': {
            'ru': 'Опишите вашу проблему или задайте вопрос. Наши специалисты ответят вам в ближайшее время.',
            'uk': 'Опишіть вашу проблему або задайте питання. Наші фахівці відповідять вам найближчим часом.',
            'en': 'Describe your problem or ask a question. Our specialists will answer you as soon as possible.'
        },
        'support_sent': {
            'ru': '✅ Ваше сообщение отправлено в поддержку! Мы ответим вам в ближайшее время.',
            'uk': '✅ Ваше повідомлення відправлено в підтримку! Ми відповімо вам найближчим часом.',
            'en': '✅ Your message has been sent to support! We will answer you as soon as possible.'
        },
        'support_cancelled': {
            'ru': '❌ Обращение в поддержку отменено.',
            'uk': '❌ Звернення до підтримки скасовано.',
            'en': '❌ Support request cancelled.'
        },
        'back_to_menu': {
            'ru': '🔙 Вернуться в меню',
            'uk': '🔙 Повернутися до меню',
            'en': '🔙 Back to menu'
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


async def process_user_message(message: types.Message):
    """
    Обработчик всех текстовых сообщений от пользователей
    Сохраняет сообщения в базу данных для просмотра в админке
    """
    user_id = message.from_user.id
    message_text = message.text

    db = DbSession()
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            return

        # Сохраняем сообщение в базу данных
        user_message = Message(
            user_id=user.id,
            message_type="text",
            content=message_text,
            telegram_message_id=message.message_id,
            is_from_admin=False
        )

        db.add(user_message)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing user message: {e}")
        db.rollback()
    finally:
        db.close()


async def process_user_photo(message: types.Message):
    """
    Обработчик фото от пользователей
    Сохраняет фото в базу данных и на диск
    """
    user_id = message.from_user.id
    caption = message.caption or ""

    db = DbSession()
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            return

        # Получаем фото наилучшего качества
        photo = message.photo[-1]

        # Создаем директорию для хранения фотографий пользователя
        os.makedirs(MESSAGES_MEDIA_DIR, exist_ok=True)

        # Генерируем уникальное имя файла
        filename = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Скачиваем файл
        await photo.download(destination_file=file_path)

        # Сохраняем сообщение в базу данных
        user_message = Message(
            user_id=user.id,
            message_type="photo",
            content=caption,
            file_path=file_path,
            telegram_message_id=message.message_id,
            is_from_admin=False
        )

        db.add(user_message)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing user photo: {e}")
        db.rollback()
    finally:
        db.close()


async def process_user_video(message: types.Message):
    """
    Обработчик видео от пользователей
    Сохраняет видео в базу данных и на диск
    """
    user_id = message.from_user.id
    caption = message.caption or ""

    db = DbSession()
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            return

        # Получаем видео
        video = message.video

        # Создаем директорию для хранения видео пользователя
        os.makedirs(MESSAGES_MEDIA_DIR, exist_ok=True)

        # Генерируем уникальное имя файла
        filename = f"{uuid.uuid4()}.mp4"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Скачиваем файл
        await video.download(destination_file=file_path)

        # Сохраняем сообщение в базу данных
        user_message = Message(
            user_id=user.id,
            message_type="video",
            content=caption,
            file_path=file_path,
            telegram_message_id=message.message_id,
            is_from_admin=False
        )

        db.add(user_message)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing user video: {e}")
        db.rollback()
    finally:
        db.close()


async def process_user_audio(message: types.Message):
    """
    Обработчик аудио от пользователей
    Сохраняет аудио в базу данных и на диск
    """
    user_id = message.from_user.id
    caption = message.caption or ""

    db = DbSession()
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            return

        # Получаем аудио
        audio = message.audio or message.voice

        if not audio:
            return

        # Создаем директорию для хранения аудио пользователя
        os.makedirs(MESSAGES_MEDIA_DIR, exist_ok=True)

        # Генерируем уникальное имя файла
        ext = "ogg" if message.voice else "mp3"
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Скачиваем файл
        await audio.download(destination_file=file_path)

        # Сохраняем сообщение в базу данных
        user_message = Message(
            user_id=user.id,
            message_type="audio",
            content=caption,
            file_path=file_path,
            telegram_message_id=message.message_id,
            is_from_admin=False
        )

        db.add(user_message)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing user audio: {e}")
        db.rollback()
    finally:
        db.close()


async def process_user_document(message: types.Message):
    """
    Обработчик документов от пользователей
    Сохраняет документы в базу данных и на диск
    """
    user_id = message.from_user.id
    caption = message.caption or ""

    db = DbSession()
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            logger.warning(f"User {user_id} not found in database")
            return

        # Получаем документ
        document = message.document

        # Создаем директорию для хранения документов пользователя
        os.makedirs(MESSAGES_MEDIA_DIR, exist_ok=True)

        # Генерируем уникальное имя файла, сохраняя оригинальное расширение
        filename = document.file_name
        ext = filename.split('.')[-1] if '.' in filename else 'doc'
        safe_filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, safe_filename)

        # Скачиваем файл
        await document.download(destination_file=file_path)

        # Сохраняем сообщение в базу данных
        user_message = Message(
            user_id=user.id,
            message_type="document",
            content=caption,
            file_path=file_path,
            telegram_message_id=message.message_id,
            is_from_admin=False
        )

        db.add(user_message)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing user document: {e}")
        db.rollback()
    finally:
        db.close()


def register_support_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики для поддержки

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Команда /support
    dp.message.register(cmd_support, Command("support"))

    # Обработка сообщений в состоянии waiting_for_message
    dp.message.register(process_support_message, SupportStates.waiting_for_message)

    # Обработка callback-запросов
    dp.callback_query.register(cancel_support,
                               lambda query: query.data == "support:cancel")