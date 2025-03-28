# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from admin.utils import serialize_model
from models.models import BugReport, BugReportMedia, User, Bot
from database.db import get_db, logger
from sqlalchemy import desc, func

router = APIRouter()

templates = Jinja2Templates(directory=Path("admin/templates"))


# Pydantic модели
class BugReportResponse(BaseModel):
    id: int
    user_id: int
    bot_id: int
    text: str
    status: str
    created_at: str
    updated_at: str


@router.get("/", response_model=List[BugReportResponse])
async def get_bug_reports(db: Session = Depends(get_db)):
    """Получение списка всех баг-репортов"""
    reports = db.query(BugReport).all()
    return [serialize_model(report) for report in reports]


@router.get("/count")
async def get_reports_count(db: Session = Depends(get_db)):
    """Получение количества баг-репортов"""
    count = db.query(BugReport).count()
    return {"count": count}


@router.get("/latest")
async def get_latest_reports(limit: int = 5, db: Session = Depends(get_db)):
    """Получение последних баг-репортов"""
    reports = db.query(BugReport).order_by(desc(BugReport.created_at)).limit(limit).all()

    return [
        {
            "id": report.id,
            "user": {
                "id": report.user.id,
                "username": report.user.username,
                "first_name": report.user.first_name
            },
            "bot": {
                "id": report.bot.id,
                "name": report.bot.name
            },
            "status": report.status,
            "created_at": report.created_at.isoformat()
        }
        for report in reports
    ]


@router.get("/{report_id}", response_model=BugReportResponse)
async def get_bug_report(report_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретном баг-репорте"""
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug report not found"
        )
    return report


@router.get("/{report_id}/media")
async def get_bug_report_media(report_id: int, db: Session = Depends(get_db)):
    """Получение медиафайлов баг-репорта"""
    # Проверяем существование баг-репорта
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug report not found"
        )

    # Получаем медиафайлы
    media_files = db.query(BugReportMedia).filter(BugReportMedia.bug_report_id == report_id).all()

    return [
        {
            "id": media.id,
            "file_path": media.file_path,
            "file_type": media.file_type,
            "url": f"/media/{media.file_path}"
        }
        for media in media_files
    ]


@router.put("/{report_id}/status")
async def update_report_status(
        report_id: int,
        status: str = Form(...),
        db: Session = Depends(get_db)
):
    """Обновление статуса баг-репорта"""
    # Проверяем существование баг-репорта
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug report not found"
        )

    # Проверяем валидность статуса
    if status not in ["new", "in_progress", "resolved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'new', 'in_progress', or 'resolved'"
        )

    # Обновляем статус
    report.status = status
    db.commit()

    return {"message": "Bug report status updated successfully"}


# Страницы админки для управления баг-репортами
@router.get("/page", response_class=templates.TemplateResponse)
async def reports_page(request: Request):
    """Страница с баг-репортами"""
    return templates.TemplateResponse("reports/index.html", {"request": request})


@router.get("/page/{report_id}", response_class=templates.TemplateResponse)
async def report_detail_page(report_id: int, request: Request, db: Session = Depends(get_db)):
    """Страница с детальной информацией о баг-репорте"""
    # Получаем информацию о баг-репорте
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug report not found"
        )

    return templates.TemplateResponse(
        "reports/detail.html",
        {"request": request, "report": report}
    )


# admin/routers/reports.py

@router.post("/{report_id}/reply")
async def reply_to_bug_report(
        report_id: int,
        message: str = Body(...),
        db: Session = Depends(get_db)
):
    """Ответ на баг-репорт"""
    # Проверяем существование баг-репорта
    report = db.query(BugReport).filter(BugReport.id == report_id).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug report not found"
        )

    # Получаем пользователя
    user = db.query(User).filter(User.id == report.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Получаем бота
    bot_item = db.query(Bot).filter(Bot.id == report.bot_id).first()

    # Формируем текст сообщения
    reply_text = f"📮 <b>Ответ на ваш баг-репорт</b>\n\n"

    if bot_item:
        reply_text += f"<b>Бот:</b> {bot_item.name}\n"

    reply_text += f"<b>Баг-репорт #{report.id}:</b>\n"
    reply_text += f"{report.text[:100]}{'...' if len(report.text) > 100 else ''}\n\n"
    reply_text += f"<b>Ответ администратора:</b>\n"
    reply_text += message

    # Отправляем ответ пользователю
    try:
        from bot.main import bot
        await bot.send_message(
            chat_id=user.telegram_id,
            text=reply_text,
            parse_mode="HTML"
        )

        # Обновляем статус баг-репорта, если он не был решен
        if report.status == "new":
            report.status = "in_progress"
            db.commit()

        return {"success": True, "message": "Reply sent successfully"}
    except Exception as e:
        logger.error(f"Error sending reply to bug report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending reply: {str(e)}"
        )


@router.post("/{report_id}/resolve")
async def resolve_bug_report(
        report_id: int,
        resolution_message: str = Body(None),
        db: Session = Depends(get_db)
):
    """Отметить баг-репорт как решенный и отправить уведомление пользователю"""
    # Проверяем существование баг-репорта
    report = db.query(BugReport).filter(BugReport.id == report_id).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug report not found"
        )

    # Получаем пользователя
    user = db.query(User).filter(User.id == report.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Получаем бота
    bot_item = db.query(Bot).filter(Bot.id == report.bot_id).first()

    # Отмечаем баг-репорт как решенный
    report.status = "resolved"
    db.commit()

    # Отправляем уведомление пользователю, если указано сообщение
    if resolution_message:
        # Формируем текст сообщения
        resolve_text = f"✅ <b>Ваш баг-репорт решен</b>\n\n"

        if bot_item:
            resolve_text += f"<b>Бот:</b> {bot_item.name}\n"

        resolve_text += f"<b>Баг-репорт #{report.id}:</b>\n"
        resolve_text += f"{report.text[:100]}{'...' if len(report.text) > 100 else ''}\n\n"

        if resolution_message:
            resolve_text += f"<b>Комментарий:</b>\n{resolution_message}"

        try:
            from bot.main import bot
            await bot.send_message(
                chat_id=user.telegram_id,
                text=resolve_text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending resolution message: {e}")
            # Не выбрасываем исключение, так как основная операция уже выполнена

    return {"success": True, "message": "Bug report marked as resolved"}


@router.get("/stats")
async def get_bug_reports_stats(db: Session = Depends(get_db)):
    """Получение статистики по баг-репортам"""
    # Общее количество баг-репортов
    total_count = db.query(BugReport).count()

    # Количество баг-репортов по статусам
    new_count = db.query(BugReport).filter(BugReport.status == "new").count()
    in_progress_count = db.query(BugReport).filter(BugReport.status == "in_progress").count()
    resolved_count = db.query(BugReport).filter(BugReport.status == "resolved").count()

    # Количество баг-репортов по ботам
    bot_stats = db.query(
        Bot.id,
        Bot.name,
        func.count(BugReport.id).label('report_count')
    ).join(
        BugReport, Bot.id == BugReport.bot_id
    ).group_by(
        Bot.id, Bot.name
    ).order_by(
        desc('report_count')
    ).limit(5).all()

    top_bots = [
        {
            "id": bot_id,
            "name": bot_name,
            "report_count": count
        }
        for bot_id, bot_name, count in bot_stats
    ]

    return {
        "total_count": total_count,
        "by_status": {
            "new": new_count,
            "in_progress": in_progress_count,
            "resolved": resolved_count
        },
        "top_bots": top_bots
    }