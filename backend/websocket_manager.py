"""
WebSocket Manager для суфлера
Управляет подключениями и рассылкой сообщений
"""

from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Менеджер WebSocket подключений"""
    
    def __init__(self):
        # {call_id: {"supervisor": WebSocket, "mode": "text/audio/hybrid"}}
        self.active_connections: Dict[str, Dict] = {}
        
        # {call_id: [список подсказок]}
        self.suggestions_queue: Dict[str, List] = {}
        
    async def connect(self, websocket: WebSocket, call_id: str, connection_type: str = "supervisor"):
        """Подключение нового клиента"""
        await websocket.accept()
        
        if call_id not in self.active_connections:
            self.active_connections[call_id] = {}
            
        self.active_connections[call_id][connection_type] = websocket
        self.active_connections[call_id]["mode"] = "hybrid"  # по умолчанию гибрид
        
        logger.info(f"✅ WebSocket подключен: {call_id} ({connection_type})")
        
    def disconnect(self, call_id: str, connection_type: str = "supervisor"):
        """Отключение клиента"""
        if call_id in self.active_connections:
            if connection_type in self.active_connections[call_id]:
                del self.active_connections[call_id][connection_type]
            
            if len(self.active_connections[call_id]) <= 1:  # только mode остался
                del self.active_connections[call_id]
                
        logger.info(f"❌ WebSocket отключен: {call_id} ({connection_type})")
        
    async def send_to_call(self, call_id: str, message: dict):
        """Отправить сообщение конкретному звонку"""
        if call_id in self.active_connections:
            connections = self.active_connections[call_id]
            
            if "supervisor" in connections:
                try:
                    await connections["supervisor"].send_json(message)
                except Exception as e:
                    logger.error(f"Ошибка отправки: {e}")
                    self.disconnect(call_id, "supervisor")
                    
    async def broadcast(self, message: dict):
        """Broadcast всем подключенным"""
        for call_id in list(self.active_connections.keys()):
            await self.send_to_call(call_id, message)
            
    async def send_text_suggestion(self, call_id: str, text: str, priority: str = "normal"):
        """Отправить текстовую подсказку"""
        message = {
            "type": "suggestion",
            "mode": "text",
            "priority": priority,
            "content": text,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_call(call_id, message)
        logger.info(f"📝 Текстовая подсказка: {call_id}")
        
    async def send_audio_suggestion(self, call_id: str, audio_url: str, text: str = None):
        """Отправить аудио подсказку"""
        message = {
            "type": "suggestion",
            "mode": "audio",
            "audio_url": audio_url,
            "text": text,  # дублируем текстом для отображения
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_call(call_id, message)
        logger.info(f"🎧 Аудио подсказка: {call_id}")
        
    async def send_hybrid_suggestion(self, call_id: str, text: str, audio_url: str, priority: str = "normal"):
        """Отправить гибридную подсказку (текст + аудио)"""
        message = {
            "type": "suggestion",
            "mode": "hybrid",
            "priority": priority,
            "text": text,
            "audio_url": audio_url,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_call(call_id, message)
        logger.info(f"🔀 Гибридная подсказка: {call_id}")
        
    async def send_transcript(self, call_id: str, speaker: str, text: str):
        """Отправить транскрипцию разговора"""
        message = {
            "type": "transcript",
            "speaker": speaker,  # client/operator
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_call(call_id, message)
        
    async def send_client_info(self, call_id: str, info: dict):
        """Отправить информацию о клиенте"""
        message = {
            "type": "client_info",
            "data": info,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_call(call_id, message)
        
    async def send_alert(self, call_id: str, alert_type: str, message_text: str):
        """Отправить критичный алерт"""
        message = {
            "type": "alert",
            "alert_type": alert_type,  # warning/danger/info
            "message": message_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_call(call_id, message)
        logger.warning(f"⚠️ Алерт: {call_id} - {message_text}")
        
    async def set_supervisor_mode(self, call_id: str, mode: str):
        """Установить режим суфлера"""
        if call_id in self.active_connections:
            self.active_connections[call_id]["mode"] = mode
            await self.send_to_call(call_id, {
                "type": "mode_changed",
                "mode": mode
            })
            logger.info(f"🎛️ Режим изменен: {call_id} -> {mode}")
            
    def get_supervisor_mode(self, call_id: str) -> str:
        """Получить текущий режим суфлера"""
        if call_id in self.active_connections:
            return self.active_connections[call_id].get("mode", "text")
        return "text"


# Глобальный экземпляр
ws_manager = ConnectionManager()

