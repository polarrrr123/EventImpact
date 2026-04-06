# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# SQLite 本地開發，部署時換 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eventimpact.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, index=True, nullable=False)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="user", cascade="all, delete")
    alerts    = relationship("Alert",     back_populates="user", cascade="all, delete")


class Portfolio(Base):
    __tablename__ = "portfolio"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker       = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    shares       = Column(Float, default=0)
    buy_price    = Column(Float, default=0)
    added_at     = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolio")


class Alert(Base):
    __tablename__ = "alerts"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker           = Column(String, nullable=False)
    company_name     = Column(String, nullable=False)
    alert_type       = Column(String, nullable=False)  # danger / warning / safe
    predicted_return = Column(Float, nullable=False)
    message          = Column(String, nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")


# ── DB 初始化 ─────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
    print("[✓] 資料庫初始化完成")


# ── Dependency ────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()