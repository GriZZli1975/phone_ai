"""
AI Consultant - автоматический консультант
Отвечает на вопросы клиентов без участия человека
"""

import logging
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from config import settings

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
set_api_key(settings.ELEVENLABS_API_KEY)


class AIConsultant:
    """AI консультант для автоматических ответов"""
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = {}
        
        # Системный промпт
        self.system_prompt = """Ты - профессиональный AI консультант колл-центра.
Твоя задача - помогать клиентам с их вопросами по телефону.

Правила общения:
1. Будь вежливым и дружелюбным
2. Давай четкие и краткие ответы
3. Если не знаешь ответ - честно скажи об этом
4. Если вопрос сложный - предложи перевести на оператора
5. Говори естественно, как живой человек
6. Используй "мы" когда говоришь о компании

Типовые вопросы которые ты можешь решить:
- Информация о продуктах/услугах
- Часы работы
- Адреса офисов
- Статус заказа (если есть номер)
- Общие вопросы

Когда переводить на оператора:
- Жалобы и недовольство
- Технические проблемы
- Возврат денег
- Сложные ситуации
- Клиент явно просит человека

Отвечай ТОЛЬКО текстом ответа, без пояснений."""
        
    async def start_conversation(self, call_id: str):
        """Начать разговор с клиентом"""
        self.conversations[call_id] = []
        
        # Приветствие
        greeting = "Здравствуйте! Я AI ассистент. Чем могу вам помочь?"
        self.conversations[call_id].append({
            "role": "assistant",
            "content": greeting
        })
        
        return greeting
        
    async def process_message(
        self, 
        call_id: str, 
        client_message: str
    ) -> Dict:
        """
        Обработать сообщение клиента
        
        Returns:
            {
                "response": "текст ответа",
                "action": "continue" | "transfer",
                "transfer_to": "sales" | "support" | None,
                "audio_url": "url_to_audio" (если включен TTS)
            }
        """
        
        if call_id not in self.conversations:
            await self.start_conversation(call_id)
            
        # Добавляем сообщение клиента
        self.conversations[call_id].append({
            "role": "user",
            "content": client_message
        })
        
        # Проверяем лимит реплик
        if len(self.conversations[call_id]) > settings.AI_CONSULTANT_MAX_TURNS * 2:
            return {
                "response": "Я вижу что ваш вопрос требует детального рассмотрения. Переведу вас на оператора.",
                "action": "transfer",
                "transfer_to": "support"
            }
            
        # Проверяем trigger слова для перевода
        transfer_check = self._check_transfer_needed(client_message)
        if transfer_check:
            return transfer_check
            
        # Генерируем ответ через GPT
        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversations[call_id]
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Добавляем в историю
            self.conversations[call_id].append({
                "role": "assistant",
                "content": ai_response
            })
            
            logger.info(f"🤖 AI ответ: {ai_response[:50]}...")
            
            # Генерируем аудио (опционально)
            audio_url = None
            # Раскомментируйте если нужно генерировать аудио для каждого ответа
            # audio_url = await self._generate_audio(ai_response)
            
            return {
                "response": ai_response,
                "action": "continue",
                "transfer_to": None,
                "audio_url": audio_url
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}", exc_info=True)
            return {
                "response": "Извините, произошла ошибка. Переведу вас на оператора.",
                "action": "transfer",
                "transfer_to": "support"
            }
            
    async def generate_audio_response(self, text: str) -> str:
        """Генерация аудио ответа через ElevenLabs"""
        return await self._generate_audio(text)
        
    async def _generate_audio(self, text: str) -> Optional[str]:
        """Внутренний метод генерации аудио"""
        try:
            audio = generate(
                text=text,
                voice=Voice(
                    voice_id=settings.ELEVENLABS_VOICE_ID,
                    settings=VoiceSettings(
                        stability=0.6,
                        similarity_boost=0.8,
                        style=0.4,
                        use_speaker_boost=True
                    )
                ),
                model="eleven_multilingual_v2"
            )
            
            # Сохраняем файл
            import uuid
            from pathlib import Path
            
            audio_id = str(uuid.uuid4())
            audio_path = Path(f"/tmp/audio/{audio_id}.mp3")
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(audio_path, "wb") as f:
                f.write(audio)
                
            audio_url = f"/api/audio/{audio_id}.mp3"
            logger.info(f"🎵 Аудио ответ сгенерирован: {audio_url}")
            return audio_url
            
        except Exception as e:
            logger.error(f"Ошибка генерации аудио: {e}")
            return None
            
    def _check_transfer_needed(self, message: str) -> Optional[Dict]:
        """Проверка нужен ли перевод на оператора"""
        message_lower = message.lower()
        
        # Явный запрос оператора
        operator_keywords = ["оператор", "человек", "сотрудник", "менеджер"]
        if any(kw in message_lower for kw in operator_keywords):
            return {
                "response": "Конечно, соединяю с оператором. Один момент.",
                "action": "transfer",
                "transfer_to": "support"
            }
            
        # Негативные ситуации
        negative_keywords = ["жалоба", "возмущен", "ужасно", "отвратительно", "верните деньги"]
        if any(kw in message_lower for kw in negative_keywords):
            return {
                "response": "Я понимаю ваше недовольство. Переведу вас на старшего специалиста.",
                "action": "transfer",
                "transfer_to": "support"
            }
            
        return None
        
    async def end_conversation(self, call_id: str):
        """Завершить разговор"""
        if call_id in self.conversations:
            del self.conversations[call_id]
            logger.info(f"Разговор завершен: {call_id}")


# Глобальный экземпляр
ai_consultant = AIConsultant()

