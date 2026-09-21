from app.database import Base
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import Table, create_engine, Integer, String, select, ForeignKey, Table, Column, DateTime, Text, LargeBinary, Boolean
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session, Mapped, mapped_column, relationship
from datetime import datetime, timezone

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    username: Mapped[str] = mapped_column(String(200))
    password: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    transactions: Mapped[list["Transaction"]] = relationship(back_populates='user')
    refresh_tokens: Mapped[list["Refresh_token"]] = relationship(back_populates = 'user')

class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[int] = mapped_column(String(200))
    date: Mapped[datetime] = mapped_column(DateTime, default = lambda: datetime.now(timezone.utc))
    cost: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped["User"] = relationship(back_populates='transactions')
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    category: Mapped["Category"] = relationship(back_populates = 'category_transactions')

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[int] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    category_transactions: Mapped[list["Transaction"]] = relationship(back_populates = 'category')


class Refresh_token(Base):
    __tablename__ = 'refresh_tokens'
    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    token: Mapped[str] = mapped_column(String(500), unique = True)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped["User"] = relationship(back_populates='refresh_tokens')