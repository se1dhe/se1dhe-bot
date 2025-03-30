# admin/routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.models import Order, BugReport, Review, Message
from database.db import get_db
from sqlalchemy import desc, and_
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def get_recent_notifications(db: Session = Depends(get_db)):
    """Получение последних уведомлений для администратора"""
    try:
        # Получаем последние заказы
        recent_orders = db.query(Order).order_by(desc(Order.created_at)).limit(5).all()
        orders_notifications = [
            {
                "id": order.id,
                "type": "order",
                "title": f"Новый заказ #{order.id}",
                "message": f"Пользователь {order.user.username or order.user.first_name or 'ID: ' + str(order.user.id)} "
                           f"заказал {order.bot.name} за {order.amount} руб.",
                "status": order.status.value,
                "link": f"/payments/page/{order.id}",
                "created_at": order.created_at.isoformat(),
                "icon": "fa-money-bill"
            }
            for order in recent_orders
        ]

        # Получаем последние баг-репорты
        recent_bug_reports = db.query(BugReport).order_by(desc(BugReport.created_at)).limit(5).all()
        bug_reports_notifications = [
            {
                "id": report.id,
                "type": "bug_report",
                "title": f"Новый баг-репорт #{report.id}",
                "message": f"Пользователь {report.user.username or report.user.first_name or 'ID: ' + str(report.user.id)} "
                           f"сообщил о проблеме с {report.bot.name}",
                "status": report.status,
                "link": f"/reports/page/{report.id}",
                "created_at": report.created_at.isoformat(),
                "icon": "fa-bug"
            }
            for report in recent_bug_reports
        ]

        # Получаем последние отзывы
        recent_reviews = db.query(Review).order_by(desc(Review.created_at)).limit(5).all()
        reviews_notifications = [
            {
                "id": review.id,
                "type": "review",
                "title": f"Новый отзыв о боте {review.bot.name}",
                "message": f"Пользователь {review.user.username or review.user.first_name or 'ID: ' + str(review.user.id)} "
                           f"оставил отзыв с рейтингом {review.rating}/5",
                "rating": review.rating,
                "link": f"/users/page/{review.user.id}",  # Пока что ссылка на пользователя, можно изменить
                "created_at": review.created_at.isoformat(),
                "icon": "fa-star"
            }
            for review in recent_reviews
        ]

        # Получаем последние сообщения от пользователей (не от админов)
        recent_messages = db.query(Message).filter(
            Message.is_from_admin == False
        ).order_by(desc(Message.created_at)).limit(5).all()

        messages_notifications = [
            {
                "id": message.id,
                "type": "message",
                "title": f"Новое сообщение от пользователя",
                "message": f"Пользователь {message.user.username or message.user.first_name or 'ID: ' + str(message.user.id)} "
                           f"отправил сообщение: {message.content[:30] + '...' if len(message.content) > 30 else message.content}",
                "link": f"/messages/page/{message.user.id}",
                "created_at": message.created_at.isoformat(),
                "icon": "fa-envelope"
            }
            for message in recent_messages
        ]

        # Объединяем все уведомления и сортируем по дате
        all_notifications = orders_notifications + bug_reports_notifications + reviews_notifications + messages_notifications
        all_notifications.sort(key=lambda x: x["created_at"], reverse=True)

        # Возвращаем общее количество и список уведомлений
        unread_count = len(all_notifications)  # В будущем можно добавить систему прочитанных уведомлений

        return {
            "unread_count": unread_count,
            "notifications": all_notifications[:10]  # Ограничиваем количество возвращаемых уведомлений
        }

    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting notifications: {str(e)}"
        )


@router.post("/mark-read")
async def mark_notifications_read():
    """
    Помечает уведомления как прочитанные
    В будущем здесь можно реализовать сохранение состояния прочитанных уведомлений
    """
    return {"success": True}