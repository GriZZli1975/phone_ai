#!/usr/bin/env python3
"""
Real-time AI обработка звонков через OpenAI Realtime API
WebSocket streaming для мгновенной обработки речи
"""
import asyncio
import json
import os
import base64
from pathlib import Path
import websockets
from fastapi import WebSocket as FastAPIWebSocket

# Manual .env loading
try:
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print("[INIT] Loaded .env for realtime")
except Exception as e:
    print(f"[WARN] Could not load .env: {e}")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"


class RealtimeAIHandler:
    """
    Real-time обработка аудио через OpenAI Realtime API
    """
    
    def __init__(self):
        self.openai_ws = None
        self.session_id = None
        
    async def connect_openai(self):
        """Подключение к OpenAI Realtime API"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.openai_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            extra_headers=headers
        )
        
        # Отправляем конфигурацию сессии
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "Ты - AI ассистент call-центра. Определи, в какой отдел нужно перевести звонок: sales (продажи), support (техподдержка), или billing (бухгалтерия). Будь краток.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        }
        
        await self.openai_ws.send(json.dumps(config))
        print("[REALTIME] Connected to OpenAI")
        
    async def send_audio_chunk(self, audio_data: bytes):
        """
        Отправка аудио чанка в OpenAI
        audio_data: PCM16 аудио данные
        """
        if not self.openai_ws:
            await self.connect_openai()
        
        # Кодируем в base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        event = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        
        await self.openai_ws.send(json.dumps(event))
        
    async def commit_audio(self):
        """Завершение отправки аудио и запрос ответа"""
        event = {
            "type": "input_audio_buffer.commit"
        }
        await self.openai_ws.send(json.dumps(event))
        
        # Создаём ответ
        response_event = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"]
            }
        }
        await self.openai_ws.send(json.dumps(response_event))
        
    async def receive_response(self):
        """
        Получение ответа от OpenAI
        Возвращает: (text, audio_chunks)
        """
        text = ""
        audio_chunks = []
        
        while True:
            try:
                message = await asyncio.wait_for(self.openai_ws.recv(), timeout=10.0)
                event = json.loads(message)
                
                event_type = event.get("type")
                
                if event_type == "response.audio.delta":
                    # Получаем аудио чанк
                    audio_base64 = event.get("delta", "")
                    if audio_base64:
                        audio_data = base64.b64decode(audio_base64)
                        audio_chunks.append(audio_data)
                        
                elif event_type == "response.text.delta":
                    # Получаем текст
                    text += event.get("delta", "")
                    
                elif event_type == "response.done":
                    # Ответ завершён
                    break
                    
                elif event_type == "error":
                    print(f"[REALTIME] Error: {event}")
                    break
                    
            except asyncio.TimeoutError:
                print("[REALTIME] Timeout waiting for response")
                break
                
        return text, audio_chunks
        
    async def close(self):
        """Закрытие соединения"""
        if self.openai_ws:
            await self.openai_ws.close()
            print("[REALTIME] Connection closed")


# Тестовый пример использования
async def test_realtime():
    """Тест real-time API"""
    handler = RealtimeAIHandler()
    await handler.connect_openai()
    
    # Симуляция отправки аудио
    # В реальности сюда придёт PCM16 аудио из Asterisk
    dummy_audio = b'\x00\x00' * 8000  # 1 секунда тишины
    
    await handler.send_audio_chunk(dummy_audio)
    await handler.commit_audio()
    
    text, audio = await handler.receive_response()
    
    print(f"[TEST] Received text: {text}")
    print(f"[TEST] Received audio chunks: {len(audio)}")
    
    await handler.close()


if __name__ == '__main__':
    asyncio.run(test_realtime())

