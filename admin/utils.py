# admin/utils.py
from datetime import datetime
from fastapi import HTTPException, status, UploadFile
from typing import List
import os
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

def datetime_to_str(dt):
    """Преобразует datetime в строку ISO формата"""
    if dt is None:
        return None
    return dt.isoformat()


def serialize_model(model_instance, exclude_fields=None):
    """
    Преобразует SQLAlchemy модель в словарь с конвертацией datetime в строки

    Args:
        model_instance: Экземпляр SQLAlchemy модели
        exclude_fields: Список полей, которые нужно исключить

    Returns:
        dict: Словарь с данными модели
    """
    if exclude_fields is None:
        exclude_fields = []

    result = {}
    for key, value in model_instance.__dict__.items():
        if key.startswith('_') or key in exclude_fields:
            continue

        if isinstance(value, datetime):
            result[key] = datetime_to_str(value)
        else:
            result[key] = value

    return result


def validate_file(file: UploadFile, allowed_extensions: List[str], max_size_mb: int = 50):
    """
    Проверяет файл на соответствие разрешенным типам и размеру.

    Args:
        file (UploadFile): Файл для проверки
        allowed_extensions (List[str]): Список разрешённых расширений (например, ['zip', 'jpg', 'png'])
        max_size_mb (int): Максимальный размер файла в МБ

    Returns:
        bool: True если файл валидный

    Raises:
        HTTPException: Если файл не соответствует требованиям
    """
    if not file.filename:
        logger.warning("Empty filename detected")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty filename"
        )

    # Проверка расширения
    ext = file.filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        logger.warning(f"Unsupported file type: {ext}. Allowed: {allowed_extensions}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Проверка размера
    try:
        # Читаем содержимое файла
        content = file.file.read()
        size_mb = len(content) / (1024 * 1024)

        if size_mb > max_size_mb:
            logger.warning(f"File too large: {size_mb}MB > {max_size_mb}MB")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File is too large. Maximum size: {max_size_mb}MB"
            )

        # Сбрасываем позицию файла в начало
        file.file.seek(0)
        return True

    except Exception as e:
        logger.error(f"Error validating file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating file: {str(e)}"
        )


def save_file(file: UploadFile, directory: Path, filename: str = None):
    """
    Сохраняет файл в указанную директорию.

    Args:
        file (UploadFile): Файл для сохранения
        directory (Path): Директория для сохранения
        filename (str, optional): Имя файла. Если None, используется оригинальное имя.

    Returns:
        Path: Путь к сохраненному файлу
    """
    try:
        # Создаем директорию, если она не существует
        os.makedirs(directory, exist_ok=True)

        # Устанавливаем имя файла
        if filename is None:
            filename = file.filename

        # Полный путь к файлу
        file_path = directory / filename

        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )