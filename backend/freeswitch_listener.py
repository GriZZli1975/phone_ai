"""
FreeSWITCH Event Listener
Слушает события из FreeSWITCH через ESL (Event Socket Layer)
"""

import asyncio
import logging
from typing import Optional
from config import settings
from websocket_manager import ws_manager
from ai.supervisor import supervisor_ai
from ai.consultant import ai_consultant
from ai.router import call_router

logger = logging.getLogger(__name__)


class FreeSwitchListener:
    """Listener для событий FreeSWITCH"""
    
    def __init__(self):
        self.connection = None
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Запуск listener"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._listen_loop())
        logger.info("✅ FreeSWITCH listener запущен")
        
    async def stop(self):
        """Остановка listener"""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("🛑 FreeSWITCH listener остановлен")
        
    async def _listen_loop(self):
        """Основной цикл прослушивания"""
        while self.running:
            try:
                await self._connect()
                await self._process_events()
            except Exception as e:
                logger.error(f"Ошибка в listener: {e}", exc_info=True)
                await asyncio.sleep(5)  # ждем перед переподключением
                
    async def _connect(self):
        """Подключение к FreeSWITCH ESL"""
        try:
            # TODO: Реальное подключение через ESL
            # from ESL import ESLconnection
            # self.connection = ESLconnection(
            #     settings.FREESWITCH_HOST,
            #     settings.FREESWITCH_PORT,
            #     settings.FREESWITCH_PASSWORD
            # )
            
            logger.info(f"🔌 Подключение к FreeSWITCH {settings.FREESWITCH_HOST}:{settings.FREESWITCH_PORT}")
            
            # Подписываемся на события
            # self.connection.events('plain', 'all')
            
        except Exception as e:
            logger.error(f"Ошибка подключения к FreeSWITCH: {e}")
            raise
            
    async def _process_events(self):
        """Обработка событий от FreeSWITCH"""
        while self.running:
            # TODO: Получение событий из FreeSWITCH
            # event = self.connection.recvEvent()
            
            # Пока заглушка для демонстрации структуры
            await asyncio.sleep(1)
            
            # Пример обработки событий:
            # await self._handle_event(event)
            
    async def _handle_event(self, event):
        """Обработка конкретного события"""
        event_name = event.getHeader("Event-Name")
        call_uuid = event.getHeader("Unique-ID")
        
        logger.debug(f"📥 Event: {event_name} | Call: {call_uuid}")
        
        # Новый звонок
        if event_name == "CHANNEL_CREATE":
            await self._handle_new_call(event)
            
        # Звонок отвечен
        elif event_name == "CHANNEL_ANSWER":
            await self._handle_call_answered(event)
            
        # Аудио данные (для real-time STT)
        elif event_name == "CUSTOM" and event.getHeader("Event-Subclass") == "audio_data":
            await self._handle_audio_data(event)
            
        # Звонок завершен
        elif event_name == "CHANNEL_HANGUP":
            await self._handle_call_hangup(event)
            
    async def _handle_new_call(self, event):
        """Обработка нового звонка"""
        call_uuid = event.getHeader("Unique-ID")
        caller_number = event.getHeader("Caller-Caller-ID-Number")
        
        logger.info(f"📞 Новый звонок: {caller_number} -> {call_uuid}")
        
        # Отправляем уведомление в админ панель
        await ws_manager.broadcast({
            "type": "new_call",
            "call_uuid": call_uuid,
            "caller_number": caller_number,
            "timestamp": asyncio.get_event_loop().time()
        })
        
    async def _handle_call_answered(self, event):
        """Звонок отвечен"""
        call_uuid = event.getHeader("Unique-ID")
        
        logger.info(f"✅ Звонок отвечен: {call_uuid}")
        
        # Запускаем AI суфлер для оператора
        operator_id = event.getHeader("variable_operator_id")
        if operator_id:
            await supervisor_ai.start_supervision(call_uuid, operator_id)
            
    async def _handle_audio_data(self, event):
        """
        Обработка аудио данных в реальном времени
        Здесь будет STT и обновление суфлера
        """
        call_uuid = event.getHeader("Unique-ID")
        # audio_data = event.getBody()
        
        # TODO: Отправка на Whisper STT
        # transcript = await whisper_transcribe(audio_data)
        
        # TODO: Обновление суфлера
        # await supervisor_ai.add_transcript(call_uuid, "client", transcript)
        
    async def _handle_call_hangup(self, event):
        """Звонок завершен"""
        call_uuid = event.getHeader("Unique-ID")
        
        logger.info(f"📴 Звонок завершен: {call_uuid}")
        
        # Останавливаем суфлер
        await supervisor_ai.stop_supervision(call_uuid)
        
        # Завершаем AI консультанта
        await ai_consultant.end_conversation(call_uuid)
        
        # Уведомляем фронтенд
        await ws_manager.send_to_call(call_uuid, {
            "type": "call_ended",
            "call_uuid": call_uuid
        })

