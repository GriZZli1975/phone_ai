"""
AI Суфлер - генерация подсказок для операторов
Поддерживает текстовый, аудио и гибридный режимы
"""

import asyncio
from typing import Dict, List, Optional
import logging
from openai import AsyncOpenAI
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from config import settings
from websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Инициализация AI сервисов
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
set_api_key(settings.ELEVENLABS_API_KEY)


class SupervisorAI:
    """AI Суфлер для операторов"""
    
    def __init__(self):
        self.active_supervisors: Dict[str, asyncio.Task] = {}
        self.conversation_history: Dict[str, List[Dict]] = {}
        
    async def start_supervision(self, call_id: str, operator_id: str):
        """Запуск суфлера для звонка"""
        if call_id in self.active_supervisors:
            logger.warning(f"Суфлер уже активен для {call_id}")
            return
            
        # Создаем задачу для мониторинга
        task = asyncio.create_task(
            self._supervise_call(call_id, operator_id)
        )
        self.active_supervisors[call_id] = task
        self.conversation_history[call_id] = []
        
        logger.info(f"🎯 Суфлер запущен для звонка {call_id}")
        
    async def stop_supervision(self, call_id: str):
        """Остановка суфлера"""
        if call_id in self.active_supervisors:
            self.active_supervisors[call_id].cancel()
            del self.active_supervisors[call_id]
            
        if call_id in self.conversation_history:
            del self.conversation_history[call_id]
            
        logger.info(f"🛑 Суфлер остановлен для звонка {call_id}")
        
    async def _supervise_call(self, call_id: str, operator_id: str):
        """Основной цикл суфлера"""
        try:
            while True:
                # Ждем обновление (каждые N секунд)
                await asyncio.sleep(settings.AI_SUPERVISOR_UPDATE_INTERVAL)
                
                # Получаем последнюю реплику клиента
                # (в реальности это будет из FreeSWITCH real-time)
                last_utterance = await self._get_last_utterance(call_id)
                
                if last_utterance:
                    # Добавляем в историю
                    self.conversation_history[call_id].append(last_utterance)
                    
                    # Генерируем подсказку
                    await self._generate_and_send_suggestion(
                        call_id, 
                        operator_id,
                        last_utterance
                    )
                    
        except asyncio.CancelledError:
            logger.info(f"Суфлер отменен для {call_id}")
        except Exception as e:
            logger.error(f"Ошибка в суфлере: {e}", exc_info=True)
            
    async def _get_last_utterance(self, call_id: str) -> Optional[Dict]:
        """Получить последнюю реплику из разговора"""
        # TODO: интеграция с FreeSWITCH для real-time STT
        # Пока заглушка для демонстрации
        return None
        
    async def _generate_and_send_suggestion(
        self, 
        call_id: str, 
        operator_id: str,
        utterance: Dict
    ):
        """Генерация и отправка подсказки"""
        
        # Получаем режим суфлера
        mode = ws_manager.get_supervisor_mode(call_id)
        
        # Генерируем текстовую подсказку через GPT
        suggestion_text = await self._generate_text_suggestion(
            call_id,
            utterance
        )
        
        if not suggestion_text:
            return
            
        # Определяем приоритет
        priority = self._determine_priority(utterance, suggestion_text)
        
        # Отправляем в зависимости от режима
        if mode == "text":
            await ws_manager.send_text_suggestion(
                call_id, 
                suggestion_text,
                priority
            )
            
        elif mode == "audio":
            # Генерируем аудио
            audio_url = await self._generate_audio_suggestion(suggestion_text)
            await ws_manager.send_audio_suggestion(
                call_id,
                audio_url,
                suggestion_text
            )
            
        elif mode == "hybrid":
            # Критичные - аудио, остальные - текст
            if priority == "critical":
                audio_url = await self._generate_audio_suggestion(suggestion_text)
                await ws_manager.send_hybrid_suggestion(
                    call_id,
                    suggestion_text,
                    audio_url,
                    priority
                )
            else:
                await ws_manager.send_text_suggestion(
                    call_id,
                    suggestion_text,
                    priority
                )
                
    async def _generate_text_suggestion(
        self, 
        call_id: str, 
        utterance: Dict
    ) -> Optional[str]:
        """Генерация текстовой подсказки через GPT"""
        
        history = self.conversation_history.get(call_id, [])
        
        # Формируем контекст для GPT
        context = self._build_context(history)
        
        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """Ты - AI суфлер для оператора колл-центра.
Твоя задача - давать КРАТКИЕ и ПОЛЕЗНЫЕ подсказки оператору во время разговора.

Правила:
1. Подсказки должны быть короткими (1-2 предложения)
2. Фокусируйся на конкретных действиях
3. Учитывай тон и эмоции клиента
4. Предлагай решения проблем
5. Напоминай о важной информации

Примеры хороших подсказок:
- "Клиент недоволен. Предложите компенсацию или ускорение доставки"
- "Спросите номер заказа для проверки статуса"
- "Клиент VIP, предоставьте приоритетное обслуживание"

НЕ делай:
- Длинные объяснения
- Очевидные советы
- Повторение того что уже сказал клиент"""
                    },
                    {
                        "role": "user",
                        "content": f"Контекст разговора:\n{context}\n\nПоследняя реплика клиента: {utterance['text']}\n\nДай подсказку оператору:"
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            suggestion = response.choices[0].message.content.strip()
            logger.info(f"💡 Подсказка сгенерирована: {suggestion[:50]}...")
            return suggestion
            
        except Exception as e:
            logger.error(f"Ошибка генерации подсказки: {e}")
            return None
            
    async def _generate_audio_suggestion(self, text: str) -> str:
        """Генерация аудио подсказки через ElevenLabs"""
        
        try:
            # Генерируем аудио с "шепчущим" голосом
            audio = generate(
                text=text,
                voice=Voice(
                    voice_id=settings.ELEVENLABS_VOICE_ID,
                    settings=VoiceSettings(
                        stability=0.5,
                        similarity_boost=0.75,
                        style=0.3,  # более нейтральный стиль
                        use_speaker_boost=True
                    )
                ),
                model="eleven_multilingual_v2"
            )
            
            # Сохраняем аудио файл
            import uuid
            from pathlib import Path
            
            audio_id = str(uuid.uuid4())
            audio_path = Path(f"/tmp/audio/{audio_id}.mp3")
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(audio_path, "wb") as f:
                f.write(audio)
                
            # Возвращаем URL
            audio_url = f"/api/audio/{audio_id}.mp3"
            logger.info(f"🎵 Аудио подсказка сгенерирована: {audio_url}")
            return audio_url
            
        except Exception as e:
            logger.error(f"Ошибка генерации аудио: {e}")
            return None
            
    def _build_context(self, history: List[Dict]) -> str:
        """Построение контекста разговора"""
        context_lines = []
        for msg in history[-5:]:  # последние 5 реплик
            speaker = "Клиент" if msg["speaker"] == "client" else "Оператор"
            context_lines.append(f"{speaker}: {msg['text']}")
        return "\n".join(context_lines)
        
    def _determine_priority(self, utterance: Dict, suggestion: str) -> str:
        """Определение приоритета подсказки"""
        
        # Ключевые слова для критичных ситуаций
        critical_keywords = [
            "отказ", "отмена", "жалоба", "возврат", "недоволен",
            "плохо", "ужасно", "проблема", "не работает"
        ]
        
        text = utterance.get("text", "").lower()
        
        for keyword in critical_keywords:
            if keyword in text:
                return "critical"
                
        return "normal"
        
    async def add_transcript(self, call_id: str, speaker: str, text: str):
        """Добавить транскрипцию реплики"""
        if call_id not in self.conversation_history:
            self.conversation_history[call_id] = []
            
        self.conversation_history[call_id].append({
            "speaker": speaker,
            "text": text,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # Отправляем транскрипцию оператору
        await ws_manager.send_transcript(call_id, speaker, text)


# Глобальный экземпляр
supervisor_ai = SupervisorAI()

