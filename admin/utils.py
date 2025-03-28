# admin/utils.py
from datetime import datetime


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