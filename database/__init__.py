# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from config.settings import DATABASE_URL
from models.models import Base
import logging


def init_db():
    """Инициализирует базу данных, создавая все таблицы"""
    logging.info("Initializing database...")

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    logging.info("Database initialized successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()