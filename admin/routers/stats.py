# admin/routers/stats.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database.db import get_db
from models.models import User, Order, Bot, Review, BugReport, OrderStatus
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def get_dashboard_stats(
        period: str = Query("month", description="Период для статистики: day, week, month, year, all"),
        db: Session = Depends(get_db)
):
    """Получение общей статистики для дашборда"""
    try:
        # Определяем начальную дату для выборки
        now = datetime.utcnow()
        start_date = None

        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        elif period == "month":
            start_date = now - timedelta(days=30)
        elif period == "year":
            start_date = now - timedelta(days=365)

        # Общее количество пользователей
        total_users = db.query(User).count()

        # Количество новых пользователей за период
        new_users = db.query(User).filter(
            User.created_at >= start_date if start_date else True
        ).count()

        # Количество заказов и сумма продаж
        orders_query = db.query(Order)
        if start_date:
            orders_query = orders_query.filter(Order.created_at >= start_date)

        total_orders = orders_query.count()

        paid_orders_query = orders_query.filter(Order.status == OrderStatus.PAID)
        paid_orders = paid_orders_query.count()

        total_sales = db.query(func.sum(Order.amount)).filter(
            Order.status == OrderStatus.PAID,
            Order.created_at >= start_date if start_date else True
        ).scalar() or 0

        # Конверсия (% оплаченных заказов)
        conversion_rate = (paid_orders / total_orders * 100) if total_orders > 0 else 0

        # Популярные боты
        popular_bots = db.query(
            Bot.id,
            Bot.name,
            func.count(Order.id).label('order_count')
        ).join(
            Order, Bot.id == Order.bot_id
        ).filter(
            Order.status == OrderStatus.PAID,
            Order.created_at >= start_date if start_date else True
        ).group_by(
            Bot.id, Bot.name
        ).order_by(
            desc('order_count')
        ).limit(5).all()

        top_bots = [
            {
                "id": bot_id,
                "name": bot_name,
                "order_count": count
            }
            for bot_id, bot_name, count in popular_bots
        ]

        # Средняя оценка ботов
        avg_rating = db.query(func.avg(Review.rating)).scalar() or 0

        # Количество баг-репортов
        bug_reports_count = db.query(BugReport).filter(
            BugReport.created_at >= start_date if start_date else True
        ).count()

        # Данные для графика продаж по дням
        sales_data = []

        if period in ["day", "week", "month"]:
            # Группировка по дням
            days = 1 if period == "day" else (7 if period == "week" else 30)
            for i in range(days):
                day_date = now - timedelta(days=days - i - 1)
                day_start = datetime(day_date.year, day_date.month, day_date.day)
                day_end = day_start + timedelta(days=1)

                day_sales = db.query(func.sum(Order.amount)).filter(
                    Order.status == OrderStatus.PAID,
                    Order.created_at >= day_start,
                    Order.created_at < day_end
                ).scalar() or 0

                sales_data.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "sales": float(day_sales)
                })
        elif period == "year":
            # Группировка по месяцам
            for i in range(12):
                month_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                month_date = month_date.replace(month=((month_date.month - i - 1) % 12 + 1))
                if month_date.month > now.month:
                    month_date = month_date.replace(year=now.year - 1)

                next_month = month_date.replace(month=month_date.month % 12 + 1)
                if next_month.month == 1:
                    next_month = next_month.replace(year=month_date.year + 1)

                month_sales = db.query(func.sum(Order.amount)).filter(
                    Order.status == OrderStatus.PAID,
                    Order.created_at >= month_date,
                    Order.created_at < next_month
                ).scalar() or 0

                sales_data.append({
                    "date": month_date.strftime("%Y-%m"),
                    "sales": float(month_sales)
                })

        return {
            "total_users": total_users,
            "new_users": new_users,
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "total_sales": float(total_sales),
            "conversion_rate": float(conversion_rate),
            "top_bots": top_bots,
            "avg_rating": float(avg_rating),
            "bug_reports_count": bug_reports_count,
            "sales_data": sales_data
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting dashboard stats: {str(e)}"
        )


@router.get("/users")
async def get_users_stats(
        period: str = Query("month", description="Период для статистики: day, week, month, year, all"),
        db: Session = Depends(get_db)
):
    """Получение статистики по пользователям"""
    try:
        # Определяем начальную дату для выборки
        now = datetime.utcnow()
        start_date = None

        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        elif period == "month":
            start_date = now - timedelta(days=30)
        elif period == "year":
            start_date = now - timedelta(days=365)

        # Общее количество пользователей
        total_users = db.query(User).count()

        # Количество новых пользователей за период
        new_users = db.query(User).filter(
            User.created_at >= start_date if start_date else True
        ).count()

        # Распределение пользователей по языкам
        language_stats = db.query(
            User.language,
            func.count(User.id).label('user_count')
        ).group_by(
            User.language
        ).all()

        languages = [
            {
                "language": lang or "unknown",
                "count": count,
                "percentage": (count / total_users * 100) if total_users > 0 else 0
            }
            for lang, count in language_stats
        ]

        # Пользователи с заказами
        users_with_orders = db.query(User.id).join(Order).distinct().count()

        # Активные пользователи (пользователи, у которых есть заказы за период)
        active_users = db.query(User.id).join(Order).filter(
            Order.created_at >= start_date if start_date else True
        ).distinct().count()

        # Данные для графика регистраций по дням
        registrations_data = []

        if period in ["day", "week", "month"]:
            # Группировка по дням
            days = 1 if period == "day" else (7 if period == "week" else 30)
            for i in range(days):
                day_date = now - timedelta(days=days - i - 1)
                day_start = datetime(day_date.year, day_date.month, day_date.day)
                day_end = day_start + timedelta(days=1)

                day_registrations = db.query(User).filter(
                    User.created_at >= day_start,
                    User.created_at < day_end
                ).count()

                registrations_data.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "registrations": day_registrations
                })
        elif period == "year":
            # Группировка по месяцам
            for i in range(12):
                month_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                month_date = month_date.replace(month=((month_date.month - i - 1) % 12 + 1))
                if month_date.month > now.month:
                    month_date = month_date.replace(year=now.year - 1)

                next_month = month_date.replace(month=month_date.month % 12 + 1)
                if next_month.month == 1:
                    next_month = next_month.replace(year=month_date.year + 1)

                month_registrations = db.query(User).filter(
                    User.created_at >= month_date,
                    User.created_at < next_month
                ).count()

                registrations_data.append({
                    "date": month_date.strftime("%Y-%m"),
                    "registrations": month_registrations
                })

        return {
            "total_users": total_users,
            "new_users": new_users,
            "users_with_orders": users_with_orders,
            "active_users": active_users,
            "languages": languages,
            "registrations_data": registrations_data
        }
    except Exception as e:
        logger.error(f"Error getting users stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting users stats: {str(e)}"
        )


@router.get("/sales")
async def get_sales_stats(
        period: str = Query("month", description="Период для статистики: day, week, month, year, all"),
        db: Session = Depends(get_db)
):
    """Получение статистики по продажам"""
    try:
        # Определяем начальную дату для выборки
        now = datetime.utcnow()
        start_date = None

        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        elif period == "month":
            start_date = now - timedelta(days=30)
        elif period == "year":
            start_date = now - timedelta(days=365)

        # Фильтр по дате
        date_filter = Order.created_at >= start_date if start_date else True

        # Общее количество заказов
        total_orders = db.query(Order).filter(date_filter).count()

        # Количество заказов по статусам
        paid_orders = db.query(Order).filter(
            date_filter,
            Order.status == OrderStatus.PAID
        ).count()

        pending_orders = db.query(Order).filter(
            date_filter,
            Order.status == OrderStatus.PENDING
        ).count()

        cancelled_orders = db.query(Order).filter(
            date_filter,
            Order.status == OrderStatus.CANCELLED
        ).count()

        # Общая сумма продаж
        total_sales = db.query(func.sum(Order.amount)).filter(
            date_filter,
            Order.status == OrderStatus.PAID
        ).scalar() or 0

        # Средний чек
        avg_order_value = total_sales / paid_orders if paid_orders > 0 else 0

        # Конверсия (% оплаченных заказов)
        conversion_rate = (paid_orders / total_orders * 100) if total_orders > 0 else 0

        # Популярные боты
        popular_bots = db.query(
            Bot.id,
            Bot.name,
            func.count(Order.id).label('order_count'),
            func.sum(Order.amount).label('total_amount')
        ).join(
            Order, Bot.id == Order.bot_id
        ).filter(
            date_filter,
            Order.status == OrderStatus.PAID
        ).group_by(
            Bot.id, Bot.name
        ).order_by(
            desc('order_count')
        ).limit(10).all()

        top_bots = [
            {
                "id": bot_id,
                "name": bot_name,
                "order_count": count,
                "total_amount": float(amount)
            }
            for bot_id, bot_name, count, amount in popular_bots
        ]

        # Статистика по платежным системам
        payment_systems = db.query(
            Order.payment_system,
            func.count(Order.id).label('order_count'),
            func.sum(Order.amount).label('total_amount')
        ).filter(
            date_filter,
            Order.status == OrderStatus.PAID,
            Order.payment_system != None
        ).group_by(
            Order.payment_system
        ).all()

        payment_stats = [
            {
                "payment_system": payment_system or "unknown",
                "order_count": count,
                "total_amount": float(amount),
                "percentage": (count / paid_orders * 100) if paid_orders > 0 else 0
            }
            for payment_system, count, amount in payment_systems
        ]

        # Данные для графика продаж по дням/месяцам
        sales_data = []

        if period in ["day", "week", "month"]:
            # Группировка по дням
            days = 1 if period == "day" else (7 if period == "week" else 30)
            for i in range(days):
                day_date = now - timedelta(days=days - i - 1)
                day_start = datetime(day_date.year, day_date.month, day_date.day)
                day_end = day_start + timedelta(days=1)

                day_sales = db.query(func.sum(Order.amount)).filter(
                    Order.status == OrderStatus.PAID,
                    Order.created_at >= day_start,
                    Order.created_at < day_end
                ).scalar() or 0

                day_orders = db.query(Order).filter(
                    Order.status == OrderStatus.PAID,
                    Order.created_at >= day_start,
                    Order.created_at < day_end
                ).count()

                sales_data.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "sales": float(day_sales),
                    "orders": day_orders
                })
        elif period == "year":
            # Группировка по месяцам
            for i in range(12):
                month_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                month_date = month_date.replace(month=((month_date.month - i - 1) % 12 + 1))
                if month_date.month > now.month:
                    month_date = month_date.replace(year=now.year - 1)

                next_month = month_date.replace(month=month_date.month % 12 + 1)
                if next_month.month == 1:
                    next_month = next_month.replace(year=month_date.year + 1)

                month_sales = db.query(func.sum(Order.amount)).filter(
                    Order.status == OrderStatus.PAID,
                    Order.created_at >= month_date,
                    Order.created_at < next_month
                ).scalar() or 0

                month_orders = db.query(Order).filter(
                    Order.status == OrderStatus.PAID,
                    Order.created_at >= month_date,
                    Order.created_at < next_month
                ).count()

                sales_data.append({
                    "date": month_date.strftime("%Y-%m"),
                    "sales": float(month_sales),
                    "orders": month_orders
                })

        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders,
            "total_sales": float(total_sales),
            "avg_order_value": float(avg_order_value),
            "conversion_rate": float(conversion_rate),
            "top_bots": top_bots,
            "payment_stats": payment_stats,
            "sales_data": sales_data
        }
    except Exception as e:
        logger.error(f"Error getting sales stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sales stats: {str(e)}"
        )

# Регистрация роутера в admin/main.py
# from admin.routers import stats
# app.include_router(stats.router, prefix="/stats", tags=["stats"], dependencies=[Depends(verify_token)])