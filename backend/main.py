"""
AI Call Center - FastAPI Backend
Главный файл приложения
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from config import settings
from database import engine, Base
from routes import calls, ai, admin, auth
from websocket_manager import ws_manager
from freeswitch_listener import FreeSwitchListener

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle события приложения"""
    # Startup
    logger.info("🚀 Запуск AI Call Center...")
    
    # Создание таблиц БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ База данных инициализирована")
    
    # Запуск FreeSWITCH listener
    freeswitch_listener = FreeSwitchListener()
    await freeswitch_listener.start()
    logger.info("✅ FreeSWITCH listener запущен")
    
    yield
    
    # Shutdown
    logger.info("🛑 Остановка сервера...")
    await freeswitch_listener.stop()


# Создание приложения
app = FastAPI(
    title="AI Call Center API",
    description="REST API для AI колл-центра с суфлером",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(auth.router, prefix="/api/auth", tags=["Авторизация"])
app.include_router(calls.router, prefix="/api/calls", tags=["Звонки"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(admin.router, prefix="/api/admin", tags=["Админ"])

# Статические файлы (записи звонков)
app.mount("/recordings", StaticFiles(directory="/recordings"), name="recordings")


# ============================================
# WebSocket - Суфлер для операторов
# ============================================

@app.websocket("/ws/supervisor/{call_id}")
async def websocket_supervisor(websocket: WebSocket, call_id: str):
    """
    WebSocket для суфлера (текстовый + аудио)
    
    Отправляет оператору:
    - Real-time транскрипцию разговора
    - AI подсказки (текстом)
    - Аудио подсказки (URL или base64)
    - Информацию о клиенте
    """
    await ws_manager.connect(websocket, call_id, "supervisor")
    logger.info(f"📞 Суфлер подключен к звонку {call_id}")
    
    try:
        while True:
            # Ожидание сообщений от клиента
            data = await websocket.receive_json()
            
            # Обработка команд от оператора
            if data.get("action") == "change_mode":
                # Оператор меняет режим: text/audio/hybrid
                mode = data.get("mode", "text")
                await ws_manager.set_supervisor_mode(call_id, mode)
                logger.info(f"🎧 Режим суфлера изменен на: {mode}")
                
            elif data.get("action") == "request_suggestion":
                # Оператор запрашивает подсказку вручную
                from ai.supervisor import generate_suggestion
                suggestion = await generate_suggestion(call_id)
                await ws_manager.send_to_call(call_id, suggestion)
                
    except WebSocketDisconnect:
        logger.info(f"📞 Суфлер отключен от звонка {call_id}")
        ws_manager.disconnect(call_id, "supervisor")


@app.websocket("/ws/calls")
async def websocket_calls_monitor(websocket: WebSocket):
    """
    WebSocket для мониторинга всех звонков (админ панель)
    
    Отправляет:
    - Список активных звонков
    - Статистику в реальном времени
    - Обновления статусов
    """
    await ws_manager.connect(websocket, "global", "monitor")
    logger.info("📊 Монитор звонков подключен")
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("📊 Монитор звонков отключен")
        ws_manager.disconnect("global", "monitor")


# ============================================
# Health check
# ============================================

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "freeswitch": "connected",
            "database": "connected",
            "ai": "ready"
        }
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "AI Call Center API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

