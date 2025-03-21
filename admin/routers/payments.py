# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.models import Order, User, Bot, OrderStatus
from database.db import get_db
from sqlalchemy import func, desc

router = APIRouter()

templates = Jinja2Templates(directory=Path("admin/templates"))


# Pydantic модели
class OrderResponse(BaseModel):
    id: int
    user_id: int
    bot_id: int
    amount: float
    status: str
    payment_system: Optional[str] = None
    payment_id: Optional[str] = None
    created_at: str
    updated_at: str


class PaymentStats(BaseModel):
    total_sales: float
    total_orders: int
    paid_orders: int
    pending_orders: int
    cancelled_orders: int


# Маршруты для платежей
@router.get("/", response_model=List[OrderResponse])
async def get_orders(db: Session = Depends(get_db)):
    """Получение списка всех заказов"""
    orders = db.query(Order).all()
    return orders


@router.get("/stats", response_model=PaymentStats)
async def get_payment_stats(db: Session = Depends(get_db)):
    """Получение статистики платежей"""
    # Получаем общую сумму продаж
    total_sales = db.query(func.sum(Order.amount)).filter(
        Order.status == OrderStatus.PAID
    ).scalar() or 0

    # Получаем количество заказов
    total_orders = db.query(Order).count()
    paid_orders = db.query(Order).filter(Order.status == OrderStatus.PAID).count()
    pending_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING).count()
    cancelled_orders = db.query(Order).filter(Order.status == OrderStatus.CANCELLED).count()

    return PaymentStats(
        total_sales=float(total_sales),
        total_orders=total_orders,
        paid_orders=paid_orders,
        pending_orders=pending_orders,
        cancelled_orders=cancelled_orders
    )


@router.get("/latest")
async def get_latest_orders(limit: int = 5, db: Session = Depends(get_db)):
    """Получение последних заказов"""
    orders = db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()

    return [
        {
            "id": order.id,
            "user": {
                "id": order.user.id,
                "username": order.user.username,
                "first_name": order.user.first_name
            },
            "bot": {
                "id": order.bot.id,
                "name": order.bot.name
            },
            "amount": order.amount,
            "status": order.status.value,
            "created_at": order.created_at.isoformat()
        }
        for order in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретном заказе"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.put("/{order_id}/status")
async def update_order_status(
        order_id: int,
        status: str,
        db: Session = Depends(get_db)
):
    """Обновление статуса заказа"""
    # Проверяем существование заказа
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Проверяем валидность статуса
    try:
        new_status = OrderStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join([s.value for s in OrderStatus])}"
        )

    # Обновляем статус
    order.status = new_status
    db.commit()

    return {"message": "Order status updated successfully"}


# Страницы админки для управления платежами
@router.get("/page", response_class=templates.TemplateResponse)
async def payments_page(request: Request):
    """Страница с заказами"""
    return templates.TemplateResponse("payments/index.html", {"request": request})


@router.get("/page/{order_id}", response_class=templates.TemplateResponse)
async def order_detail_page(order_id: int, request: Request, db: Session = Depends(get_db)):
    """Страница с детальной информацией о заказе"""
    # Получаем информацию о заказе
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return templates.TemplateResponse(
        "payments/detail.html",
        {"request": request, "order": order}
    )