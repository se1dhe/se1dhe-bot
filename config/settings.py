# -*- coding: utf-8 -*-
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Настройки приложения
DEBUG = os.getenv("DEBUG", "True") == "True"
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@localhost/se1dhe_bot")

# Настройки Telegram бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# Настройки платежных систем
FREEKASSA_API_KEY = os.getenv("FREEKASSA_API_KEY", "")
FREEKASSA_SHOP_ID = os.getenv("FREEKASSA_SHOP_ID", "")
FREEKASSA_SECRET_KEY = os.getenv("FREEKASSA_SECRET_KEY", "")

PAYKASSA_API_KEY = os.getenv("PAYKASSA_API_KEY", "")
PAYKASSA_SHOP_ID = os.getenv("PAYKASSA_SHOP_ID", "")
PAYKASSA_SECRET_KEY = os.getenv("PAYKASSA_SECRET_KEY", "")

# Настройки медиа файлов
MEDIA_ROOT = BASE_DIR / "media"
BOT_FILES_DIR = MEDIA_ROOT / "bot_files"
BUG_REPORTS_DIR = MEDIA_ROOT / "bug_reports"

# Настройки Telegraph
TELEGRAPH_TOKEN = os.getenv("TELEGRAPH_TOKEN", "")

# Настройки Admin API
ADMIN_API_HOST = os.getenv("ADMIN_API_HOST", "0.0.0.0")
ADMIN_API_PORT = int(os.getenv("ADMIN_API_PORT", "8000"))

# Поддерживаемые языки
SUPPORTED_LANGUAGES = ["ru", "uk", "en"]
DEFAULT_LANGUAGE = "ru"

# Создаем директории, если они не существуют
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(BOT_FILES_DIR, exist_ok=True)
os.makedirs(BUG_REPORTS_DIR, exist_ok=True)