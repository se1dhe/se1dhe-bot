# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import DATABASE_URL

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

Base = declarative_base()

def get_db():
    """Функция-генератор для получения сессии базы данных"""
    db = Session()
    try:
        yield db
    finally:
        db.close()