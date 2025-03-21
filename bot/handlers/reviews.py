# -*- coding: utf-8 -*-
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text
from sqlalchemy.orm import Session
from models.models import User, Bot, Review
from database.db import Session as DbSession
from config.settings import DEFAULT_LANGUAGE
import logging

logger = logging.getLogger(__name__)


# Определяем состояния FSM
class ReviewStates(StatesGroup):
    waiting_for_bot = State()
    waiting_for_rating = State()
    waiting_for_text = State()


async def cmd_review(message: types.Message, state: FSMContext):
    """
    Обработчик команды /review
    Начинает процесс оставления отзыва
    """
    language = message.from_user.language_code or DEFAULT_LANGUAGE
    user_id = message.from_user.id

    # Получаем список ботов, купленных пользователем
    # В реальном приложении здесь должен быть запрос к БД
    # Сейчас используем заглушку
    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            await message.answer(
                get_localized_text('error_user_not_found', language)
            )
            return

        # Здесь должен быть код для получения списка ботов, которые купил пользователь
        # Для заглушки просто берем первые 3 бота из БД
        purchased_bots = db.query(Bot).limit(3).all()

        if not purchased_bots:
            await message.answer(
                get_localized_text('review_no_bots', language),
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

        # Формируем клавиатуру с выбором бота
        keyboard = InlineKeyboardMarkup(row_width=1)

        for bot in purchased_bots:
            keyboard.add(InlineKeyboardButton(
                text=bot.name,
                callback_data=f"review:bot:{bot.id}"
            ))

        # Добавляем кнопку отмены
        keyboard.add(InlineKeyboardButton(
            text=get_localized_text('cancel', language),
            callback_data="review:cancel"
        ))

        # Отправляем сообщение с выбором бота
        await message.answer(
            get_localized_text('review_select_bot', language),
            reply_markup=keyboard
        )

        # Устанавливаем состояние
        await state.set_state(ReviewStates.waiting_for_bot)

    except Exception as e:
        logger.error(f"Error in review command: {e}")
        await message.answer(get_localized_text('error_general', language))
    finally:
        db.close()


async def process_bot_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор бота для отзыва
    """
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    # Получаем ID бота из callback_data
    bot_id = int(callback.data.split(':')[2])

    # Сохраняем ID бота в state
    await state.update_data(bot_id=bot_id)

    # Отвечаем на callback
    await callback.answer()

    # Формируем клавиатуру для выбора рейтинга
    keyboard = InlineKeyboardMarkup(row_width=5)

    # Добавляем кнопки рейтинга
    rating_buttons = []
    for i in range(1, 6):
        rating_buttons.append(InlineKeyboardButton(
            text=f"{i} ⭐",
            callback_data=f"review:rating:{i}"
        ))

    keyboard.add(*rating_buttons)

    # Добавляем кнопку отмены
    keyboard.add(InlineKeyboardButton(
        text=get_localized_text('cancel', language),
        callback_data="review:cancel"
    ))

    # Отправляем сообщение с выбором рейтинга
    await callback.message.edit_text(
        get_localized_text('review_select_rating', language),
        reply_markup=keyboard
    )

    # Устанавливаем состояние
    await state.set_state(ReviewStates.waiting_for_rating)


async def process_rating_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор рейтинга для отзыва
    """
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    # Получаем рейтинг из callback_data
    rating = int(callback.data.split(':')[2])

    # Сохраняем рейтинг в state
    await state.update_data(rating=rating)

    # Отвечаем на callback
    await callback.answer()

    # Отправляем запрос текста отзыва
    await callback.message.edit_text(
        get_localized_text('review_enter_text', language) + "\n\n" +
        get_localized_text('review_skip_text', language),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_localized_text('review_skip', language),
                    callback_data="review:skip_text"
                )],
                [InlineKeyboardButton(
                    text=get_localized_text('cancel', language),
                    callback_data="review:cancel"
                )]
            ]
        )
    )

    # Устанавливаем состояние
    await state.set_state(ReviewStates.waiting_for_text)


async def process_review_text(message: types.Message, state: FSMContext):
    """
    Обрабатывает текст отзыва
    """
    language = message.from_user.language_code or DEFAULT_LANGUAGE
    user_id = message.from_user.id

    # Получаем данные из state
    data = await state.get_data()
    bot_id = data.get('bot_id')
    rating = data.get('rating')

    # Сохраняем отзыв
    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            await message.answer(
                get_localized_text('error_user_not_found', language)
            )
            return

        # Получаем бота
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            await message.answer(
                get_localized_text('error_bot_not_found', language)
            )
            return

        # Создаем новый отзыв
        review = Review(
            user_id=user.id,
            bot_id=bot_id,
            rating=rating,
            text=message.text
        )

        db.add(review)
        db.commit()

        # Отправляем подтверждение
        await message.answer(
            get_localized_text('review_thanks', language),
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

    except Exception as e:
        logger.error(f"Error saving review: {e}")
        await message.answer(get_localized_text('error_general', language))
    finally:
        db.close()


async def skip_review_text(callback: types.CallbackQuery, state: FSMContext):
    """
    Пропускает ввод текста отзыва
    """
    language = callback.from_user.language_code or DEFAULT_LANGUAGE
    user_id = callback.from_user.id

    # Получаем данные из state
    data = await state.get_data()
    bot_id = data.get('bot_id')
    rating = data.get('rating')

    # Отвечаем на callback
    await callback.answer()

    # Сохраняем отзыв без текста
    db = DbSession()
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            await callback.message.edit_text(
                get_localized_text('error_user_not_found', language)
            )
            return

        # Получаем бота
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            await callback.message.edit_text(
                get_localized_text('error_bot_not_found', language)
            )
            return

        # Создаем новый отзыв без текста
        review = Review(
            user_id=user.id,
            bot_id=bot_id,
            rating=rating,
            text=None
        )

        db.add(review)
        db.commit()

        # Отправляем подтверждение
        await callback.message.edit_text(
            get_localized_text('review_thanks', language),
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

    except Exception as e:
        logger.error(f"Error saving review: {e}")
        await callback.message.edit_text(get_localized_text('error_general', language))
    finally:
        db.close()


async def cancel_review(callback: types.CallbackQuery, state: FSMContext):
    """
    Отменяет процесс оставления отзыва
    """
    language = callback.from_user.language_code or DEFAULT_LANGUAGE

    # Отвечаем на callback
    await callback.answer()

    # Сбрасываем состояние
    await state.clear()

    # Отправляем сообщение об отмене
    await callback.message.edit_text(
        get_localized_text('review_cancelled', language),
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
    # Базовые тексты для отзывов
    texts = {
        'review_select_bot': {
            'ru': '⭐ Выберите бота, о котором хотите оставить отзыв:',
            'uk': '⭐ Виберіть бота, про якого хочете залишити відгук:',
            'en': '⭐ Select the bot you want to review:'
        },
        'review_select_rating': {
            'ru': 'Оцените бота от 1 до 5 звезд:',
            'uk': 'Оцініть бота від 1 до 5 зірок:',
            'en': 'Rate the bot from 1 to 5 stars:'
        },
        'review_enter_text': {
            'ru': 'Напишите свой отзыв (или нажмите кнопку "Пропустить" для отзыва без текста):',
            'uk': 'Напишіть свій відгук (або натисніть кнопку "Пропустити" для відгуку без тексту):',
            'en': 'Write your review (or press the "Skip" button for a review without text):'
        },
        'review_skip_text': {
            'ru': 'Вы также можете не писать текст, а просто оставить оценку.',
            'uk': 'Ви також можете не писати текст, а просто залишити оцінку.',
            'en': 'You can also just leave a rating without writing text.'
        },
        'review_skip': {
            'ru': 'Пропустить',
            'uk': 'Пропустити',
            'en': 'Skip'
        },
        'review_thanks': {
            'ru': '✅ Спасибо за ваш отзыв! Он поможет нам сделать наших ботов лучше.',
            'uk': '✅ Дякуємо за ваш відгук! Він допоможе нам зробити наших ботів кращими.',
            'en': '✅ Thank you for your review! It will help us make our bots better.'
        },
        'review_cancelled': {
            'ru': '❌ Отзыв отменен.',
            'uk': '❌ Відгук скасовано.',
            'en': '❌ Review cancelled.'
        },
        'review_no_bots': {
            'ru': 'У вас нет купленных ботов для оставления отзыва. Посетите каталог, чтобы приобрести бота.',
            'uk': 'У вас немає куплених ботів для залишення відгуку. Відвідайте каталог, щоб придбати бота.',
            'en': 'You have no purchased bots to leave a review. Visit the catalog to purchase a bot.'
        },
        'error_user_not_found': {
            'ru': 'Ошибка: пользователь не найден. Пожалуйста, перезапустите бота командой /start.',
            'uk': 'Помилка: користувача не знайдено. Будь ласка, перезапустіть бота командою /start.',
            'en': 'Error: user not found. Please restart the bot with the /start command.'
        },
        'error_bot_not_found': {
            'ru': 'Ошибка: бот не найден.',
            'uk': 'Помилка: бота не знайдено.',
            'en': 'Error: bot not found.'
        },
        'error_general': {
            'ru': 'Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку.',
            'uk': 'Сталася помилка. Будь ласка, спробуйте пізніше або зверніться до підтримки.',
            'en': 'An error occurred. Please try again later or contact support.'
        },
        'catalog': {
            'ru': '🛒 Перейти в каталог',
            'uk': '🛒 Перейти до каталогу',
            'en': '🛒 Go to catalog'
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


def register_reviews_handlers(dp: Dispatcher):
    """
    Регистрирует обработчики для отзывов

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Команда /review
    dp.message.register(cmd_review, Command("review"))

    # Обработка callback-запросов
    dp.callback_query.register(process_bot_selection,
                               lambda query: query.data.startswith("review:bot:"))
    dp.callback_query.register(process_rating_selection,
                               lambda query: query.data.startswith("review:rating:"))
    dp.callback_query.register(skip_review_text,
                               lambda query: query.data == "review:skip_text")
    dp.callback_query.register(cancel_review,
                               lambda query: query.data == "review:cancel")

    # Обработка текста отзыва
    dp.message.register(process_review_text, ReviewStates.waiting_for_text)