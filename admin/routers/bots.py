# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pathlib import Path
import os
import shutil
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.models import Bot, BotCategory, BotMedia
from database.db import get_db
from config.settings import BOT_FILES_DIR, MEDIA_ROOT
import telegraph
from config.settings import TELEGRAPH_TOKEN

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

    # Проверяем, есть ли боты в этой категории
    bots_count = db.query(Bot).filter(Bot.category_id == category_id).count()
    if bots_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with bots. Remove bots first or change their category."
        )

    db.delete(db_category)
    db.commit()
    return {"message": "Category deleted successfully"}


# Маршруты для ботов
@router.get("/", response_model=List[BotResponse])
async def get_bots(db: Session = Depends(get_db)):
    """Получение списка всех ботов"""
    bots = db.query(Bot).all()
    return bots


@router.get("/count")
async def get_bots_count(db: Session = Depends(get_db)):
    """Получение количества ботов"""
    count = db.query(Bot).count()
    return {"count": count}


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
    # Проверяем существование категории, если указана
    if category_id:
        category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

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
    if archive_file:
        # Создаем директорию для файлов бота, если она не существует
        bot_dir = BOT_FILES_DIR / str(bot.id)
        os.makedirs(bot_dir, exist_ok=True)

        # Сохраняем архив
        archive_path = bot_dir / f"{archive_file.filename}"
        with open(archive_path, "wb") as buffer:
            shutil.copyfileobj(archive_file.file, buffer)

        # Обновляем путь к архиву в БД
        bot.archive_path = str(archive_path.relative_to(MEDIA_ROOT))
        db.commit()

    # Создаем README в Telegraph, если предоставлен контент
    if readme_content:
        try:
            # Инициализируем клиент Telegraph
            telegraph_client = telegraph.Telegraph(TELEGRAPH_TOKEN)

            # Создаем страницу
            response = telegraph_client.create_page(
                title=f"README: {bot.name}",
                html_content=readme_content,
                author_name="SE1DHE Bot"
            )

            # Получаем URL страницы
            url = f"https://telegra.ph/{response['path']}"

            # Обновляем URL README в БД
            bot.readme_url = url
            db.commit()
        except Exception as e:
            # Логируем ошибку, но продолжаем (README не критичен)
            print(f"Error creating Telegraph page: {e}")

    db.refresh(bot)
    return bot


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
    if category_id is not None:
        # Проверяем существование категории
        if category_id > 0:
            category = db.query(BotCategory).filter(BotCategory.id == category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )
        bot.category_id = category_id if category_id > 0 else None
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
            print(f"Error updating Telegraph page: {e}")

    db.commit()
    db.refresh(bot)
    return bot


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
        {"request": request, "categories": categories}
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
            "categories": categories,
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


@router.get("/page/categories", response_class=templates.TemplateResponse)
async def categories_page(request: Request):
    """Страница со списком категорий ботов"""
    return templates.TemplateResponse("bots/categories.html", {"request": request})