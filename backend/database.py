"""
База данных - модели и подключение
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON
from datetime import datetime
from config import settings

# Создание engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base для моделей
Base = declarative_base()


# ============================================
# Модели базы данных
# ============================================

class Call(Base):
    """Модель звонка"""
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(100), unique=True, index=True)
    caller_number = Column(String(20))
    called_number = Column(String(20))
    direction = Column(String(10))  # inbound/outbound
    status = Column(String(20))  # active/completed/failed
    
    # Временные метки
    start_time = Column(DateTime, default=datetime.utcnow)
    answer_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, default=0)  # секунды
    
    # AI обработка
    ai_handled = Column(Boolean, default=False)
    ai_routed_to = Column(String(50), nullable=True)  # sales/support/consultant
    ai_confidence = Column(Float, nullable=True)
    
    # Запись
    recording_path = Column(String(255), nullable=True)
    transcript = Column(Text, nullable=True)
    
    # Метаданные
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Suggestion(Base):
    """Модель подсказок суфлера"""
    __tablename__ = "suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    call_uuid = Column(String(100), index=True)
    
    # Тип подсказки
    suggestion_type = Column(String(20))  # text/audio/critical
    
    # Контент
    text = Column(Text)
    audio_url = Column(String(255), nullable=True)
    
    # AI данные
    confidence = Column(Float)
    context = Column(JSON, nullable=True)
    
    # Была ли показана оператору
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    
    # Оценка от оператора (полезная/бесполезная)
    rating = Column(Integer, nullable=True)  # 1-5
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Operator(Base):
    """Модель оператора"""
    __tablename__ = "operators"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    
    # SIP данные
    sip_extension = Column(String(10), unique=True)
    sip_password = Column(String(50))
    
    # Настройки
    department = Column(String(50))  # sales/support/etc
    supervisor_mode = Column(String(20), default="text")  # text/audio/hybrid
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    current_call_uuid = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RoutingRule(Base):
    """Правила маршрутизации AI"""
    __tablename__ = "routing_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    
    # Условия
    keywords = Column(JSON)  # список ключевых слов
    intent = Column(String(50))  # detected intent
    priority = Column(Integer, default=0)
    
    # Действие
    route_to = Column(String(50))  # department/extension/ai
    
    # Активность
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================
# Dependency для получения сессии
# ============================================

async def get_db():
    """Dependency для получения database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

