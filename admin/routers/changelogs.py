# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.models import Changelog, Bot
from database.db import get_db
from sqlalchemy import desc

router = APIRouter()

templates = Jinja2Templates(directory=Path("admin/templates"))


# Pydantic модели
class ChangelogCreate(BaseModel):
    bot_id: int
    version: str
    description: str


class ChangelogResponse(BaseModel):
    id: int
    bot_id: int
    version: str
    description: str
    is_notified: bool
    created_at: str


# Маршруты для ченжлогов
@router.get("/", response_model=List[ChangelogResponse])
async def get_changelogs(db: Session = Depends(get_db)):
    """Получение списка всех ченжлогов"""
    changelogs = db.query(Changelog).order_by(desc(Changelog.created_at)).all()
    return changelogs


@router.get("/bot/{bot_id}", response_model=List[ChangelogResponse])
async def get_bot_changelogs(bot_id: int, db: Session = Depends(get_db)):
    """Получение списка ченжлогов для конкретного бота"""
    # Проверяем существование бота
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    changelogs = db.query(Changelog).filter(Changelog.bot_id == bot_id).order_by(desc(Changelog.created_at)).all()
    return changelogs


@router.post("/", response_model=ChangelogResponse)
async def create_changelog(
        bot_id: int = Form(...),
        version: str = Form(...),
        description: str = Form(...),
        db: Session = Depends(get_db)
):
    """Создание нового ченжлога"""
    # Проверяем существование бота
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    # Создаем запись ченжлога
    changelog = Changelog(
        bot_id=bot_id,
        version=version,
        description=description,
        is_notified=False
    )
    db.add(changelog)
    db.commit()
    db.refresh(changelog)

    return changelog


@router.put("/{changelog_id}/notify")
async def mark_as_notified(changelog_id: int, db: Session = Depends(get_db)):
    """Отметить ченжлог как отправленный"""
    # Получаем ченжлог из БД
    changelog = db.query(Changelog).filter(Changelog.id == changelog_id).first()
    if not changelog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog not found"
        )

    # Обновляем статус уведомления
    changelog.is_notified = True
    db.commit()

    return {"message": "Changelog marked as notified"}


@router.delete("/{changelog_id}")
async def delete_changelog(changelog_id: int, db: Session = Depends(get_db)):
    """Удаление ченжлога"""
    # Получаем ченжлог из БД
    changelog = db.query(Changelog).filter(Changelog.id == changelog_id).first()
    if not changelog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog not found"
        )

    # Удаляем ченжлог
    db.delete(changelog)
    db.commit()

    return {"message": "Changelog deleted successfully"}


# Страницы админки для управления ченжлогами
@router.get("/page", response_class=templates.TemplateResponse)
async def changelogs_page(request: Request, db: Session = Depends(get_db)):
    """Страница с ченжлогами"""
    # Получаем список ботов для выпадающего списка
    bots = db.query(Bot).all()

    return templates.TemplateResponse(
        "changelogs/index.html",
        {"request": request, "bots": bots}
    )


@router.get("/page/{bot_id}", response_class=templates.TemplateResponse)
async def bot_changelogs_page(bot_id: int, request: Request, db: Session = Depends(get_db)):
    """Страница с ченжлогами конкретного бота"""
    # Получаем бота из БД
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    return templates.TemplateResponse(
        "changelogs/bot.html",
        {"request": request, "bot": bot}
    )