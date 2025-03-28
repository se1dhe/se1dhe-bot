# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pathlib import Path
import os
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from models.models import User, Message
from database.db import get_db
from config.settings import MEDIA_ROOT, MESSAGES_MEDIA_DIR

router = APIRouter()
templates = Jinja2Templates(directory=Path("admin/templates"))
logger = logging.getLogger(__name__)

# Проверяем существование директории для медиафайлов сообщений
os.makedirs(MESSAGES_MEDIA_DIR, exist_ok=True)


@router.post("/send-text")
async def send_text_message(
        user_id: int = Body(...),
        message_text: str = Body(...),
        parse_mode: str = Body("html"),
        db: Session = Depends(get_db)
):
    """
    Отправляет текстовое сообщение пользователю

    Args:
        user_id: ID пользователя в базе данных
        message_text: Текст сообщения
        parse_mode: Режим форматирования текста (html, markdown, none)
    """
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Пользователь не найден"}
            )

        # Импортируем бота напрямую из модуля
        from bot.main import bot

        # Отправляем сообщение пользователю через бота
        if parse_mode.lower() == "none":
            parse_mode = None

        sent_message = await bot.send_message(
            chat_id=user.telegram_id,
            text=message_text,
            parse_mode=parse_mode
        )

        # Сохраняем сообщение в базе данных
        message = Message(
            user_id=user.id,
            message_type="text",
            content=message_text,
            telegram_message_id=sent_message.message_id,
            is_from_admin=True
        )
        db.add(message)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Сообщение успешно отправлено"}
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"Ошибка при отправке сообщения: {str(e)}"}
        )


@router.post("/send-photo")
async def send_photo_message(
        user_id: int = Form(...),
        caption: Optional[str] = Form(None),
        parse_mode: str = Form("html"),
        photo: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Отправляет изображение пользователю

    Args:
        user_id: ID пользователя в базе данных
        caption: Подпись к изображению (опционально)
        parse_mode: Режим форматирования подписи (html, markdown, none)
        photo: Файл изображения
    """
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Пользователь не найден"}
            )

        # Проверяем тип файла (только изображения)
        content_type = photo.content_type
        if not content_type.startswith("image/"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "Неправильный тип файла. Ожидается изображение."}
            )

        # Генерируем уникальное имя файла
        ext = photo.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await photo.read())

        # Импортируем бота напрямую из модуля
        from bot.main import bot

        # Отправляем изображение пользователю через бота
        if parse_mode and parse_mode.lower() == "none":
            parse_mode = None

        with open(file_path, "rb") as photo_file:
            sent_message = await bot.send_photo(
                chat_id=user.telegram_id,
                photo=photo_file,
                caption=caption,
                parse_mode=parse_mode
            )

        # Сохраняем сообщение в базе данных
        message = Message(
            user_id=user.id,
            message_type="photo",
            content=caption or "",
            file_path=file_path,
            telegram_message_id=sent_message.message_id,
            is_from_admin=True
        )
        db.add(message)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Изображение успешно отправлено"}
        )

    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"Ошибка при отправке изображения: {str(e)}"}
        )


@router.post("/send-video")
async def send_video_message(
        user_id: int = Form(...),
        caption: Optional[str] = Form(None),
        parse_mode: str = Form("html"),
        video: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Отправляет видео пользователю

    Args:
        user_id: ID пользователя в базе данных
        caption: Подпись к видео (опционально)
        parse_mode: Режим форматирования подписи (html, markdown, none)
        video: Файл видео
    """
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Пользователь не найден"}
            )

        # Проверяем тип файла (только видео)
        content_type = video.content_type
        if not content_type.startswith("video/"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "Неправильный тип файла. Ожидается видео."}
            )

        # Генерируем уникальное имя файла
        ext = video.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await video.read())

        # Импортируем бота напрямую из модуля
        from bot.main import bot

        # Отправляем видео пользователю через бота
        if parse_mode and parse_mode.lower() == "none":
            parse_mode = None

        with open(file_path, "rb") as video_file:
            sent_message = await bot.send_video(
                chat_id=user.telegram_id,
                video=video_file,
                caption=caption,
                parse_mode=parse_mode
            )

        # Сохраняем сообщение в базе данных
        message = Message(
            user_id=user.id,
            message_type="video",
            content=caption or "",
            file_path=file_path,
            telegram_message_id=sent_message.message_id,
            is_from_admin=True
        )
        db.add(message)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Видео успешно отправлено"}
        )

    except Exception as e:
        logger.error(f"Error sending video: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"Ошибка при отправке видео: {str(e)}"}
        )


@router.post("/send-audio")
async def send_audio_message(
        user_id: int = Form(...),
        caption: Optional[str] = Form(None),
        parse_mode: str = Form("html"),
        audio: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Отправляет аудио пользователю

    Args:
        user_id: ID пользователя в базе данных
        caption: Подпись к аудио (опционально)
        parse_mode: Режим форматирования подписи (html, markdown, none)
        audio: Файл аудио
    """
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Пользователь не найден"}
            )

        # Проверяем тип файла (только аудио)
        content_type = audio.content_type
        if not content_type.startswith("audio/"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "Неправильный тип файла. Ожидается аудио."}
            )

        # Генерируем уникальное имя файла
        ext = audio.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await audio.read())

        # Импортируем бота напрямую из модуля
        from bot.main import bot

        # Отправляем аудио пользователю через бота
        if parse_mode and parse_mode.lower() == "none":
            parse_mode = None

        with open(file_path, "rb") as audio_file:
            sent_message = await bot.send_audio(
                chat_id=user.telegram_id,
                audio=audio_file,
                caption=caption,
                parse_mode=parse_mode
            )

        # Сохраняем сообщение в базе данных
        message = Message(
            user_id=user.id,
            message_type="audio",
            content=caption or "",
            file_path=file_path,
            telegram_message_id=sent_message.message_id,
            is_from_admin=True
        )
        db.add(message)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Аудио успешно отправлено"}
        )

    except Exception as e:
        logger.error(f"Error sending audio: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"Ошибка при отправке аудио: {str(e)}"}
        )


@router.post("/send-document")
async def send_document_message(
        user_id: int = Form(...),
        caption: Optional[str] = Form(None),
        parse_mode: str = Form("html"),
        document: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Отправляет документ пользователю

    Args:
        user_id: ID пользователя в базе данных
        caption: Подпись к документу (опционально)
        parse_mode: Режим форматирования подписи (html, markdown, none)
        document: Файл документа
    """
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Пользователь не найден"}
            )

        # Генерируем уникальное имя файла
        ext = document.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(MESSAGES_MEDIA_DIR, filename)

        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await document.read())

        # Импортируем бота напрямую из модуля
        from bot.main import bot

        # Отправляем документ пользователю через бота
        if parse_mode and parse_mode.lower() == "none":
            parse_mode = None

        with open(file_path, "rb") as doc_file:
            sent_message = await bot.send_document(
                chat_id=user.telegram_id,
                document=doc_file,
                caption=caption,
                parse_mode=parse_mode
            )

        # Сохраняем сообщение в базе данных
        message = Message(
            user_id=user.id,
            message_type="document",
            content=caption or "",
            file_path=file_path,
            telegram_message_id=sent_message.message_id,
            is_from_admin=True
        )
        db.add(message)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Документ успешно отправлен"}
        )

    except Exception as e:
        logger.error(f"Error sending document: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"Ошибка при отправке документа: {str(e)}"}
        )


@router.get("/message-history/{user_id}")
async def get_message_history(
        user_id: int,
        limit: int = 50,
        db: Session = Depends(get_db)
):
    """
    Получает историю сообщений с пользователем

    Args:
        user_id: ID пользователя в базе данных
        limit: Максимальное количество сообщений
    """
    try:
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Пользователь не найден"}
            )

        # Получаем сообщения из базы данных
        messages = db.query(Message).filter(
            Message.user_id == user_id
        ).order_by(Message.created_at.desc()).limit(limit).all()

        # Преобразуем в список словарей
        message_list = []
        for msg in messages:
            message_list.append({
                "id": msg.id,
                "type": msg.message_type,
                "content": msg.content,
                "is_from_admin": msg.is_from_admin,
                "file_path": msg.file_path,
                "created_at": msg.created_at.isoformat(),
                "media_url": f"/media/messages/{os.path.basename(msg.file_path)}" if msg.file_path else None
            })

        return message_list

    except Exception as e:
        logger.error(f"Error getting message history: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"Ошибка при получении истории сообщений: {str(e)}"}
        )


@router.get("/page/{user_id}")
async def message_page(
        user_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """Страница для отправки сообщений пользователю"""
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Пользователь не найден", "status_code": 404}
        )

    return templates.TemplateResponse(
        "messages/index.html",
        {"request": request, "user": user}
    )