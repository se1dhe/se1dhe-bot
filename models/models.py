# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import datetime

Base = declarative_base()


class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language = Column(String(2), default="ru")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Отношения
    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    bug_reports = relationship("BugReport", back_populates="user")


class BotCategory(Base):
    __tablename__ = "bot_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    discount = Column(Float, default=0)

    # Отношения
    bots = relationship("Bot", back_populates="category")


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("bot_categories.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    discount = Column(Float, default=0)
    archive_path = Column(String(500), nullable=True)
    readme_url = Column(String(500), nullable=True)
    support_group_link = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Отношения
    category = relationship("BotCategory", back_populates="bots")
    media_files = relationship("BotMedia", back_populates="bot")
    orders = relationship("Order", back_populates="bot")
    reviews = relationship("Review", back_populates="bot")
    bug_reports = relationship("BugReport", back_populates="bot")
    changelog_entries = relationship("Changelog", back_populates="bot")


class BotMedia(Base):
    __tablename__ = "bot_media"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # photo, video
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Отношения
    bot = relationship("Bot", back_populates="media_files")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_system = Column(String(50), nullable=True)
    payment_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="orders")
    bot = relationship("Bot", back_populates="orders")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="reviews")
    bot = relationship("Bot", back_populates="reviews")


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(50), default="new")  # new, in_progress, resolved
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="bug_reports")
    bot = relationship("Bot", back_populates="bug_reports")
    media_files = relationship("BugReportMedia", back_populates="bug_report")


class BugReportMedia(Base):
    __tablename__ = "bug_report_media"

    id = Column(Integer, primary_key=True)
    bug_report_id = Column(Integer, ForeignKey("bug_reports.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # photo, video
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Отношения
    bug_report = relationship("BugReport", back_populates="media_files")


class Changelog(Base):
    __tablename__ = "changelogs"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    is_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Отношения
    bot = relationship("Bot", back_populates="changelog_entries")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Отношения
    items = relationship("CartItem", back_populates="cart")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Отношения
    cart = relationship("Cart", back_populates="items")
    bot = relationship("Bot")