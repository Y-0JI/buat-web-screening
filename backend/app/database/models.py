from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    scan_histories = relationship("ScanHistory", back_populates="user", cascade="all, delete-orphan")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(10), nullable=False)
    note = Column(Text, nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="watchlists")




class ListedTicker(Base):
    __tablename__ = "listed_tickers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, unique=True)
    company_name = Column(String(255), nullable=True)
    sector = Column(String(255), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ListedTicker(ticker={self.ticker})>"


class ScanHistory(Base):
    __tablename__ = "scan_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(10), nullable=False)
    score = Column(Float, nullable=True)
    verdict = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="scan_histories")