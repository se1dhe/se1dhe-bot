FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY .. .

# Создание директорий для медиа файлов
RUN mkdir -p media/bot_files media/bug_reports

# Настройка переменных окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Запускаем приложение по умолчанию
CMD ["python", "-m", "bot.main"]