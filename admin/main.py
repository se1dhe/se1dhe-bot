# admin/main.py
# -*- coding: utf-8 -*-
import uvicorn
import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pathlib import Path
from database.db import Session as DbSession, get_db, Session
from models.models import User, Bot, BotCategory, BotMedia, BugReport, Order
from admin.routers import messages
from admin.routers import notifications
import logging

# Настроим логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем импорты роутеров
from admin.routers import auth, webhooks, bots, users, payments, reports, changelogs
from admin.middleware.auth_middleware import verify_token, get_token_from_request
from config.settings import ADMIN_API_HOST, ADMIN_API_PORT, SECRET_KEY, MESSAGES_MEDIA_DIR

# Получаем абсолютный путь к директории, где находится файл скрипта
BASE_DIR = Path(__file__).resolve().parent

# Создаем директории для статических файлов, если их нет
os.makedirs(BASE_DIR / "static", exist_ok=True)
os.makedirs(BASE_DIR / "static/css", exist_ok=True)
os.makedirs(BASE_DIR / "static/js", exist_ok=True)

# Отключаем временно OpenAPI для решения проблемы с документацией
app = FastAPI(
    title="SE1DHE Bot Admin API",
    description="Admin panel API for managing the Telegram bot shop",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/media/messages", StaticFiles(directory=str(MESSAGES_MEDIA_DIR)), name="messages_media")

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Регистрация маршрутов для авторизации
app.include_router(auth.router)

# Маршруты вебхуков (публичные)
app.include_router(webhooks.router)


# Глобальная обработка исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# Маршруты для HTML страниц (без проверки токена)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Перенаправление на страницу входа"""
    return templates.TemplateResponse("auth/auth.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная страница админ-панели"""
    return templates.TemplateResponse("dashboard/index.html", {"request": request})


# Страницы для управления ботами
@app.get("/bots/page", response_class=HTMLResponse)
async def bots_page(request: Request):
    """Страница со списком ботов"""
    return templates.TemplateResponse("bots/index.html", {"request": request})


@app.get("/bots/page/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    """Страница со списком категорий ботов"""
    return templates.TemplateResponse("bots/categories.html", {"request": request})


@app.get("/bots/page/create", response_class=HTMLResponse)
async def create_bot_page(request: Request):
    """Страница создания нового бота"""
    db = DbSession()
    try:
        # Получаем список категорий для выпадающего списка
        categories = db.query(BotCategory).all()
        return templates.TemplateResponse(
            "bots/create.html",
            {"request": request, "categories.js": categories}
        )
    except Exception as e:
        logger.error(f"Error loading categories.js: {e}")
        return templates.TemplateResponse(
            "bots/create.html",
            {"request": request, "categories.js": []}
        )
    finally:
        db.close()


@app.get("/bots/page/{bot_id}/edit", response_class=HTMLResponse)
async def edit_bot_page(bot_id: int, request: Request):
    """Страница редактирования бота"""
    db = DbSession()
    try:
        # Получаем информацию о боте
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Bot not found", "status_code": 404}
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
    except Exception as e:
        logger.error(f"Error loading bot edit page: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": f"Error: {str(e)}", "status_code": 500}
        )
    finally:
        db.close()


# Страницы пользователей
@app.get("/users/page", response_class=HTMLResponse)
async def users_page(request: Request):
    """Страница со списком пользователей"""
    return templates.TemplateResponse("users/index.html", {"request": request})


@app.get("/users/page/{user_id}", response_class=HTMLResponse)
async def user_detail_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Страница с детальной информацией о пользователе"""
    # Получаем информацию о пользователе
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "User not found", "status_code": 404}
        )

    return templates.TemplateResponse(
        "users/detail.html",
        {"request": request, "user": user}
    )


# Страницы платежей
@app.get("/payments/page", response_class=HTMLResponse)
async def payments_page(request: Request):
    """Страница с заказами"""
    return templates.TemplateResponse("payments/index.html", {"request": request})


@app.get("/payments/page/{order_id}", response_class=HTMLResponse)
async def order_detail_page(order_id: int, request: Request):
    """Страница с детальной информацией о заказе"""
    db = DbSession()
    try:
        # Получаем информацию о заказе
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Order not found", "status_code": 404}
            )

        return templates.TemplateResponse(
            "payments/detail.html",
            {"request": request, "order": order}
        )
    except Exception as e:
        logger.error(f"Error loading order detail page: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": f"Error: {str(e)}", "status_code": 500}
        )
    finally:
        db.close()


# Страницы баг-репортов
@app.get("/reports/page", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Страница с баг-репортами"""
    return templates.TemplateResponse("reports/index.html", {"request": request})


@app.get("/reports/page/{report_id}", response_class=HTMLResponse)
async def report_detail_page(report_id: int, request: Request):
    """Страница с детальной информацией о баг-репорте"""
    db = DbSession()
    try:
        # Получаем информацию о баг-репорте
        report = db.query(BugReport).filter(BugReport.id == report_id).first()
        if not report:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Bug report not found", "status_code": 404}
            )

        return templates.TemplateResponse(
            "reports/detail.html",
            {"request": request, "report": report}
        )
    except Exception as e:
        logger.error(f"Error loading report detail page: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": f"Error: {str(e)}", "status_code": 500}
        )
    finally:
        db.close()


# Страницы ченжлогов
@app.get("/changelogs/page", response_class=HTMLResponse)
async def changelogs_page(request: Request):
    """Страница с ченжлогами"""
    db = DbSession()
    try:
        # Получаем список ботов для выпадающего списка
        bots = db.query(Bot).all()

        return templates.TemplateResponse(
            "changelogs/index.html",
            {"request": request, "bots": bots}
        )
    except Exception as e:
        logger.error(f"Error loading changelogs page: {e}")
        return templates.TemplateResponse(
            "changelogs/index.html",
            {"request": request, "bots": []}
        )
    finally:
        db.close()


@app.get("/changelogs/page/{bot_id}", response_class=HTMLResponse)
async def bot_changelogs_page(bot_id: int, request: Request):
    """Страница с ченжлогами конкретного бота"""
    db = DbSession()
    try:
        # Получаем бота из БД
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Bot not found", "status_code": 404}
            )

        return templates.TemplateResponse(
            "changelogs/bot.html",
            {"request": request, "bot": bot}
        )
    except Exception as e:
        logger.error(f"Error loading bot changelogs page: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": f"Error: {str(e)}", "status_code": 500}
        )
    finally:
        db.close()


# Страница с ошибкой (для обработки 404, 500 и т.д.)
@app.get("/error", response_class=HTMLResponse)
async def error_page(request: Request, message: str = "Unknown error", status_code: int = 500):
    """Страница с ошибкой"""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "message": message, "status_code": status_code}
    )

@app.get("/messages/page/{user_id}", response_class=HTMLResponse)
async def message_page(user_id: int, request: Request):
    """Страница для отправки сообщений пользователю"""
    db = DbSession()
    try:
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
    except Exception as e:
        logger.error(f"Error loading message page: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": f"Error: {str(e)}", "status_code": 500}
        )
    finally:
        db.close()

# API маршруты с проверкой токена (добавим после HTML-маршрутов)
api_routes = [
    (bots.router, "/bots", "bots"),
    (users.router, "/users", "users"),
    (payments.router, "/payments", "payments"),
    (reports.router, "/reports", "reports"),
    (changelogs.router, "/changelogs", "changelogs"),
    (messages.router, "/messages", "messages"),
    (notifications.router, "/notifications", "notifications"),  # Добавлено
]

for router, prefix, tag in api_routes:
    app.include_router(router, prefix=prefix, tags=[tag], dependencies=[Depends(verify_token)])

if __name__ == "__main__":
    uvicorn.run(
        "admin.main:app",
        host=ADMIN_API_HOST,
        port=ADMIN_API_PORT,
        reload=True
    )