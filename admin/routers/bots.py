# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File, Body
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import shutil
from typing import List, Optional, Dict
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from admin.utils import serialize_model, validate_file
from models.models import Bot, BotCategory, BotMedia
from database.db import get_db, execute_with_retry
from config.settings import BOT_FILES_DIR, MEDIA_ROOT
import telegraph
from config.settings import TELEGRAPH_TOKEN
import logging


logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory=Path("admin/templates"))


# Pydantic модели
class BotCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    discount: float = 0


class BotCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount: float


class BotCreate(BaseModel):
    name: str
    description: str
    price: float
    category_id: Optional[int] = None
    discount: float = 0
    support_group_link: Optional[str] = None


class BotResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category_id: Optional[int] = None
    discount: float
    archive_path: Optional[str] = None
    readme_url: Optional[str] = None
    support_group_link: Optional[str] = None
    created_at: str
    updated_at: str


# Маршруты для категорий ботов
@router.post("/categories", response_model=BotCategoryResponse)
async def create_category(category: BotCategoryCreate, db: Session = Depends(get_db)):
    """Создание новой категории ботов"""
    db_category = BotCategory(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/categories", response_model=List[BotCategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """Получение списка всех категорий ботов"""
    categories = db.query(BotCategory).all()
    return categories


@router.get("/categories/{category_id}", response_model=BotCategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретной категории ботов"""
    category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.put("/categories/{category_id}", response_model=BotCategoryResponse)
async def update_category(
        category_id: int,
        category_update: BotCategoryCreate,
        db: Session = Depends(get_db)
):
    """Обновление категории ботов"""
    db_category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    for key, value in category_update.dict().items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)
    return db_category


@router.delete("/categories/{category_id}")
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Удаление категории ботов"""
    db_category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Получаем все боты в данной категории
    bots_in_category = db.query(Bot).filter(Bot.category_id == category_id).all()

    # Устанавливаем category_id = None для всех ботов в этой категории
    for bot in bots_in_category:
        bot.category_id = None

    # Удаляем категорию
    db.delete(db_category)
    db.commit()

    return {
        "message": f"Category deleted successfully. {len(bots_in_category)} bots were moved to 'No category' state."}


@router.get("/categories/stats")
async def get_categories_stats(db: Session = Depends(get_db)):
    """Получение статистики по категориям"""
    try:
        # Получаем все категории
        categories = db.query(BotCategory).all()

        # Подготавливаем результат
        result = []

        # Для каждой категории считаем количество ботов и общую сумму
        for category in categories:
            bots_count = db.query(Bot).filter(Bot.category_id == category.id).count()
            total_price = db.query(func.sum(Bot.price)).filter(Bot.category_id == category.id).scalar() or 0

            result.append({
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "discount": category.discount,
                "bots_count": bots_count,
                "total_price": float(total_price)
            })

        # Также добавляем статистику для ботов без категории
        uncategorized_count = db.query(Bot).filter(Bot.category_id == None).count()
        uncategorized_price = db.query(func.sum(Bot.price)).filter(Bot.category_id == None).scalar() or 0

        result.append({
            "id": None,
            "name": "Без категории",
            "description": None,
            "discount": 0,
            "bots_count": uncategorized_count,
            "total_price": float(uncategorized_price)
        })

        return result
    except Exception as e:
        logger.error(f"Error getting categories stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting categories stats: {str(e)}"
        )

# Маршруты для ботов
@router.get("/", response_model=List[BotResponse])
async def get_bots(db: Session = Depends(get_db)):
    """Получение списка всех ботов"""
    bots = db.query(Bot).all()
    return [serialize_model(bot) for bot in bots]


@router.get("/count")
async def get_bots_count(db: Session = Depends(get_db)):
    """Получение количества ботов"""
    try:
        # Обертываем запрос в функцию retry
        def count_bots():
            return db.query(func.count(Bot.id)).scalar() or 0

        count = execute_with_retry(count_bots)
        return {"count": count}
    except Exception as e:
        logger.error(f"Error while counting bots: {e}")
        # Возвращаем нулевое значение в случае ошибки
        return {"count": 0}


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретном боте"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    return bot


@router.post("/", response_model=BotResponse)
async def create_bot(
        name: str = Form(...),
        description: str = Form(...),
        price: float = Form(...),
        category_id: Optional[int] = Form(None),
        discount: float = Form(0),
        support_group_link: Optional[str] = Form(None),
        archive_file: Optional[UploadFile] = File(None),
        readme_content: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """Создание нового бота"""
    try:
        # Проверяем существование категории, если указана
        category_discount = 0
        if category_id and int(category_id) > 0:
            category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )
            category_discount = category.discount
            # Преобразуем category_id в int или None
            category_id = int(category_id)
        else:
            category_id = None

        # Если не указана скидка для бота, используем скидку категории
        if discount == 0 and category_discount > 0:
            discount = category_discount

        # Создаем запись бота в БД
        bot = Bot(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            discount=discount,
            support_group_link=support_group_link
        )
        db.add(bot)
        db.commit()
        db.refresh(bot)

        # Обрабатываем загрузку архива, если предоставлен
        if archive_file and archive_file.filename:
            try:
                # Создаем директорию для файлов бота, если она не существует
                bot_dir = BOT_FILES_DIR / str(bot.id)
                os.makedirs(bot_dir, exist_ok=True)

                # Проверяем расширение файла
                file_ext = archive_file.filename.split('.')[-1].lower()
                if file_ext not in ['zip', 'rar', '7z']:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid archive format. Allowed formats: zip, rar, 7z"
                    )

                # Генерируем безопасное имя файла
                safe_filename = f"bot_{bot.id}_archive.{file_ext}"

                # Сохраняем архив
                archive_path = bot_dir / safe_filename
                with open(archive_path, "wb") as buffer:
                    shutil.copyfileobj(archive_file.file, buffer)

                # Обновляем путь к архиву в БД
                bot.archive_path = str(archive_path.relative_to(MEDIA_ROOT))
                db.commit()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error saving archive file: {e}")
                # Продолжаем выполнение, даже если возникла ошибка с архивом

        # Создаем README в Telegraph, если предоставлен контент
        if readme_content and readme_content.strip():
            try:
                # Используем нашу утилиту для создания Telegraph страницы
                from utils.telegraph_utils import create_telegraph_page

                # Создаем страницу
                url = create_telegraph_page(
                    title=f"README: {bot.name}",
                    content=readme_content,
                    author="SE1DHE Bot"
                )

                if url:
                    # Обновляем URL README в БД
                    bot.readme_url = url
                    db.commit()
            except Exception as e:
                logger.error(f"Error creating Telegraph page: {e}")
                # Продолжаем выполнение, даже если возникла ошибка с README

        db.refresh(bot)
        return bot
    except HTTPException:
        # Пробрасываем HTTP исключения дальше
        raise
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating bot: {str(e)}"
        )


@router.get("/{bot_id}/readme-content")
async def get_readme_content(bot_id: int, db: Session = Depends(get_db)):
    """Получение содержимого README для бота"""
    try:
        # Получаем информацию о боте
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot or not bot.readme_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot README not found"
            )

        # Получаем HTML-контент с Telegra.ph
        from utils.telegraph_utils import get_telegraph_content

        content = get_telegraph_content(bot.readme_url)
        return {"content": content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting README content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting README content: {str(e)}"
        )


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
        bot_id: int,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        category_id: Optional[int] = Form(None),
        discount: Optional[float] = Form(None),
        support_group_link: Optional[str] = Form(None),
        archive_file: Optional[UploadFile] = File(None),
        readme_content: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """Обновление информации о боте"""
    try:
        # Получаем бота из БД
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )

        # Обновляем базовую информацию
        if name is not None:
            bot.name = name
        if description is not None:
            bot.description = description
        if price is not None:
            bot.price = price

        # Проверяем и обновляем категорию
        if category_id is not None:
            # Если передано значение > 0, проверяем существование категории
            if category_id > 0:
                category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Category not found"
                    )
                # Если пользователь не указал скидку, а у категории есть скидка, используем её
                if discount is None and category.discount > 0:
                    bot.discount = category.discount
            bot.category_id = category_id if category_id > 0 else None

        # Обновляем скидку, если указана
        if discount is not None:
            bot.discount = discount

        if support_group_link is not None:
            bot.support_group_link = support_group_link

        # Обрабатываем загрузку архива, если предоставлен
        if archive_file:
            # Создаем директорию для файлов бота, если она не существует
            bot_dir = BOT_FILES_DIR / str(bot.id)
            os.makedirs(bot_dir, exist_ok=True)

            # Удаляем старый архив, если он существует
            if bot.archive_path:
                old_archive_path = MEDIA_ROOT / bot.archive_path
                if os.path.exists(old_archive_path):
                    os.remove(old_archive_path)

            # Сохраняем новый архив
            archive_path = bot_dir / f"{archive_file.filename}"
            with open(archive_path, "wb") as buffer:
                shutil.copyfileobj(archive_file.file, buffer)

            # Обновляем путь к архиву в БД
            bot.archive_path = str(archive_path.relative_to(MEDIA_ROOT))

        # Обновляем README в Telegraph, если предоставлен контент
        if readme_content:
            try:
                # Инициализируем клиент Telegraph
                telegraph_client = telegraph.Telegraph(TELEGRAPH_TOKEN)

                # Если уже есть README, обновляем его
                if bot.readme_url and '/telegraph/' in bot.readme_url:
                    # Извлекаем path из URL
                    path = bot.readme_url.split('/')[-1]

                    # Обновляем страницу
                    response = telegraph_client.edit_page(
                        path=path,
                        title=f"README: {bot.name}",
                        html_content=readme_content,
                        author_name="SE1DHE Bot"
                    )
                else:
                    # Создаем новую страницу
                    response = telegraph_client.create_page(
                        title=f"README: {bot.name}",
                        html_content=readme_content,
                        author_name="SE1DHE Bot"
                    )

                    # Получаем URL страницы
                    url = f"https://telegra.ph/{response['path']}"

                    # Обновляем URL README в БД
                    bot.readme_url = url
            except Exception as e:
                # Логируем ошибку, но продолжаем (README не критичен)
                logger.error(f"Error updating Telegraph page: {e}")

        db.commit()
        db.refresh(bot)
        return bot
    except HTTPException:
        # Пробрасываем HTTP исключения дальше
        raise
    except Exception as e:
        logger.error(f"Error updating bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating bot: {str(e)}"
        )


@router.delete("/{bot_id}")
async def delete_bot(bot_id: int, db: Session = Depends(get_db)):
    """Удаление бота"""
    # Получаем бота из БД
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Удаляем все связанные медиафайлы
    db.query(BotMedia).filter(BotMedia.bot_id == bot_id).delete()

    # Удаляем бота из БД
    db.delete(bot)
    db.commit()

    # Удаляем директорию с файлами бота
    bot_dir = BOT_FILES_DIR / str(bot_id)
    if os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)

    return {"message": "Bot deleted successfully"}


# Маршруты для медиафайлов бота
@router.post("/{bot_id}/media")
async def add_bot_media(
        bot_id: int,
        file_type: str = Form(...),  # photo или video
        media_file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Добавление медиафайла к боту"""
    # Проверяем существование бота
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Проверяем тип файла
    if file_type not in ["photo", "video"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Must be 'photo' or 'video'"
        )

    # Создаем директорию для медиафайлов бота, если она не существует
    media_dir = BOT_FILES_DIR / str(bot_id) / "media"
    os.makedirs(media_dir, exist_ok=True)

    # Сохраняем медиафайл
    file_path = media_dir / f"{file_type}_{media_file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(media_file.file, buffer)

    # Создаем запись о медиафайле в БД
    bot_media = BotMedia(
        bot_id=bot_id,
        file_path=str(file_path.relative_to(MEDIA_ROOT)),
        file_type=file_type
    )
    db.add(bot_media)
    db.commit()
    db.refresh(bot_media)

    return {
        "id": bot_media.id,
        "bot_id": bot_id,
        "file_path": bot_media.file_path,
        "file_type": file_type
    }


@router.get("/{bot_id}/media")
async def get_bot_media(bot_id: int, db: Session = Depends(get_db)):
    """Получение списка медиафайлов бота"""
    # Проверяем существование бота
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Получаем все медиафайлы бота
    media_files = db.query(BotMedia).filter(BotMedia.bot_id == bot_id).all()

    return [
        {
            "id": media.id,
            "bot_id": bot_id,
            "file_path": media.file_path,
            "file_type": media.file_type,
            "url": f"/media/{media.file_path}"
        }
        for media in media_files
    ]


@router.delete("/{bot_id}/media/{media_id}")
async def delete_bot_media(bot_id: int, media_id: int, db: Session = Depends(get_db)):
    """Удаление медиафайла бота"""
    # Получаем медиафайл из БД
    media = db.query(BotMedia).filter(
        BotMedia.id == media_id,
        BotMedia.bot_id == bot_id
    ).first()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found or does not belong to this bot"
        )

    # Удаляем файл с диска
    file_path = MEDIA_ROOT / media.file_path
    if os.path.exists(file_path):
        os.remove(file_path)

    # Удаляем запись из БД
    db.delete(media)
    db.commit()

    return {"message": "Media deleted successfully"}


# Страницы админки для управления ботами
@router.get("/page", response_class=templates.TemplateResponse)
async def bots_page(request: Request):
    """Страница со списком ботов"""
    return templates.TemplateResponse("bots/index.html", {"request": request})


@router.get("/page/create", response_class=templates.TemplateResponse)
async def create_bot_page(request: Request, db: Session = Depends(get_db)):
    """Страница создания нового бота"""
    # Получаем список категорий для выпадающего списка
    categories = db.query(BotCategory).all()

    return templates.TemplateResponse(
        "bots/create.html",
        {"request": request, "categories.js": categories}
    )


@router.get("/page/{bot_id}/edit", response_class=templates.TemplateResponse)
async def edit_bot_page(bot_id: int, request: Request, db: Session = Depends(get_db)):
    """Страница редактирования бота"""
    # Получаем информацию о боте
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Получаем список категорий для выпадающего списка
    categories = db.query(BotCategory).all()

    # Получаем медиафайлы бота
    media_files = db.query(BotMedia).filter(BotMedia.bot_id == bot_id).all()

    return templates.TemplateResponse(
        "bots/edit.html",
        {
            "request": request,
            "bot": bot,
            "categories.js": categories,
            "media_files": [
                {
                    "id": media.id,
                    "file_path": media.file_path,
                    "file_type": media.file_type,
                    "url": f"/media/{media.file_path}"
                }
                for media in media_files
            ]
        }
    )


# admin/routers/bots.py

@router.post("/{bot_id}/media/bulk", response_model=List[Dict])
async def add_bot_media_bulk(
        bot_id: int,
        media_files: List[UploadFile] = File(...),
        db: Session = Depends(get_db)
):
    """Добавление нескольких медиафайлов к боту"""
    # Проверяем существование бота
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Создаем директорию для медиафайлов бота, если она не существует
    media_dir = BOT_FILES_DIR / str(bot_id) / "media"
    os.makedirs(media_dir, exist_ok=True)

    added_media = []

    for media_file in media_files:
        # Определяем тип файла
        file_type = "photo"
        mime_type = media_file.content_type
        if mime_type and mime_type.startswith("video"):
            file_type = "video"

        # Валидация файла
        try:
            allowed_extensions = ["jpg", "jpeg", "png", "gif"] if file_type == "photo" else ["mp4", "avi", "mov"]
            max_size_mb = 10 if file_type == "photo" else 50

            validate_file(media_file, allowed_extensions, max_size_mb)

            # Сохраняем медиафайл
            file_path = media_dir / f"{file_type}_{media_file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(media_file.file, buffer)

            # Создаем запись о медиафайле в БД
            bot_media = BotMedia(
                bot_id=bot_id,
                file_path=str(file_path.relative_to(MEDIA_ROOT)),
                file_type=file_type
            )
            db.add(bot_media)
            db.commit()
            db.refresh(bot_media)

            added_media.append({
                "id": bot_media.id,
                "bot_id": bot_id,
                "file_path": bot_media.file_path,
                "file_type": file_type,
                "url": f"/media/{bot_media.file_path}"
            })

        except Exception as e:
            logger.error(f"Error adding media file {media_file.filename}: {e}")
            # Продолжаем с другими файлами

    return added_media


@router.put("/{bot_id}/media/{media_id}", response_model=Dict)
async def update_bot_media(
        bot_id: int,
        media_id: int,
        file_type: str = Form(...),
        db: Session = Depends(get_db)
):
    """Обновление типа медиафайла бота"""
    # Проверяем существование медиафайла
    media = db.query(BotMedia).filter(
        BotMedia.id == media_id,
        BotMedia.bot_id == bot_id
    ).first()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found or does not belong to this bot"
        )

    # Проверяем тип файла
    if file_type not in ["photo", "video"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Must be 'photo' or 'video'"
        )

    # Обновляем тип файла
    media.file_type = file_type
    db.commit()
    db.refresh(media)

    return {
        "id": media.id,
        "bot_id": bot_id,
        "file_path": media.file_path,
        "file_type": media.file_type,
        "url": f"/media/{media.file_path}"
    }


@router.post("/{bot_id}/media/reorder", response_model=Dict)
async def reorder_bot_media(
        bot_id: int,
        order: List[int] = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    """Изменение порядка медиафайлов бота"""
    # Проверяем существование бота
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Получаем все медиафайлы бота
    media_files = db.query(BotMedia).filter(BotMedia.bot_id == bot_id).all()
    media_ids = [media.id for media in media_files]

    # Проверяем, что все ID из order существуют в media_ids
    if not all(media_id in media_ids for media_id in order):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media IDs in order"
        )

    # Обновляем порядок (предполагается, что у BotMedia есть поле order)
    # Если такого поля нет, нужно добавить его через миграцию
    for i, media_id in enumerate(order):
        db.query(BotMedia).filter(BotMedia.id == media_id).update({"order": i})

    db.commit()

    return {"success": True, "message": "Media order updated successfully"}


@router.get("/page/categories", response_class=templates.TemplateResponse)
async def categories_page(request: Request):
    """Страница со списком категорий ботов"""
    return templates.TemplateResponse("bots/categories.js.html", {"request": request})