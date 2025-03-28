# -*- coding: utf-8 -*-
import uvicorn
import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

from admin.middleware.auth_middleware import verify_token
from admin.routers import auth, bots, users, payments, reports, changelogs
from config.settings import ADMIN_API_HOST, ADMIN_API_PORT, SECRET_KEY

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

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Регистрация всех маршрутов
app.include_router(auth.router)
app.include_router(bots.router, prefix="/bots", tags=["bots"], dependencies=[Depends(verify_token)])
app.include_router(users.router, prefix="/users", tags=["users"], dependencies=[Depends(verify_token)])
app.include_router(payments.router, prefix="/payments", tags=["payments"], dependencies=[Depends(verify_token)])
app.include_router(reports.router, prefix="/reports", tags=["reports"], dependencies=[Depends(verify_token)])
app.include_router(changelogs.router, prefix="/changelogs", tags=["changelogs"], dependencies=[Depends(verify_token)])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Перенаправление на страницу входа"""
    return templates.TemplateResponse("auth/auth.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная страница админ-панели"""
    # Получаем токен из localStorage через JS
    return templates.TemplateResponse("dashboard/index.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(
        "admin.main:app",
        host=ADMIN_API_HOST,
        port=ADMIN_API_PORT,
        reload=True
    )