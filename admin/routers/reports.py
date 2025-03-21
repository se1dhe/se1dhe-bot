# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.models import BugReport, BugReportMedia, User, Bot
from database.db import get_db
from sqlalchemy import desc

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


# Маршруты для баг-репортов
@router.get("/", response_model=List[BugReportResponse])
async def get_bug_reports(db: Session = Depends(get_db)):
    """Получение списка всех баг-репортов"""
    reports = db.query(BugReport).all()
    return reports


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