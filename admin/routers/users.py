# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from admin.utils import serialize_model
from models.models import User, Order, Review, BugReport
from database.db import get_db
from sqlalchemy import func

router = APIRouter()

templates = Jinja2Templates(directory=Path("admin/templates"))


# Pydantic модели
class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str
    created_at: str


class UserStats(BaseModel):
    total_orders: int
    total_spent: float
    reviews_count: int
    bug_reports_count: int


@router.get("/", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    """Получение списка всех пользователей"""
    users = db.query(User).all()

    # Используем serialize_model для правильной сериализации datetime полей
    serialized_users = [serialize_model(user) for user in users]

    return serialized_users


@router.get("/count")
async def get_users_count(db: Session = Depends(get_db)):
    """Получение количества пользователей"""
    count = db.query(User).count()
    return {"count": count}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретном пользователе"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """Получение статистики пользователя"""
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Получаем статистику заказов
    total_orders = db.query(Order).filter(Order.user_id == user_id).count()
    total_spent = db.query(func.sum(Order.amount)).filter(Order.user_id == user_id).scalar() or 0

    # Получаем количество отзывов
    reviews_count = db.query(Review).filter(Review.user_id == user_id).count()

    # Получаем количество баг-репортов
    bug_reports_count = db.query(BugReport).filter(BugReport.user_id == user_id).count()

    return UserStats(
        total_orders=total_orders,
        total_spent=float(total_spent),
        reviews_count=reviews_count,
        bug_reports_count=bug_reports_count
    )


@router.get("/{user_id}/orders")
async def get_user_orders(user_id: int, db: Session = Depends(get_db)):
    """Получение списка заказов пользователя"""
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Получаем заказы пользователя
    orders = db.query(Order).filter(Order.user_id == user_id).all()

    return [
        {
            "id": order.id,
            "bot_id": order.bot_id,
            "bot_name": order.bot.name,
            "amount": order.amount,
            "status": order.status.value,
            "payment_system": order.payment_system,
            "created_at": order.created_at.isoformat()
        }
        for order in orders
    ]


@router.get("/{user_id}/reviews")
async def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
    """Получение списка отзывов пользователя"""
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Получаем отзывы пользователя
    reviews = db.query(Review).filter(Review.user_id == user_id).all()

    return [
        {
            "id": review.id,
            "bot_id": review.bot_id,
            "bot_name": review.bot.name,
            "text": review.text,
            "rating": review.rating,
            "created_at": review.created_at.isoformat()
        }
        for review in reviews
    ]


@router.get("/{user_id}/bug_reports")
async def get_user_bug_reports(user_id: int, db: Session = Depends(get_db)):
    """Получение списка баг-репортов пользователя"""
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Получаем баг-репорты пользователя
    bug_reports = db.query(BugReport).filter(BugReport.user_id == user_id).all()

    return [
        {
            "id": report.id,
            "bot_id": report.bot_id,
            "bot_name": report.bot.name,
            "text": report.text,
            "status": report.status,
            "created_at": report.created_at.isoformat()
        }
        for report in bug_reports
    ]


# Страницы админки для управления пользователями
@router.get("/page", response_class=templates.TemplateResponse)
async def users_page(request: Request):
    """Страница со списком пользователей"""
    return templates.TemplateResponse("users/index.html", {"request": request})


@router.get("/page/{user_id}", response_class=templates.TemplateResponse)
async def user_detail_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Страница с детальной информацией о пользователе"""
    # Получаем информацию о пользователе
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return templates.TemplateResponse(
        "users/detail.html",
        {"request": request, "user": user}
    )