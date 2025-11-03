#!/usr/bin/env python3
"""
ARI Real-time обработчик для стриминга аудио в OpenAI
"""
import asyncio
import json
import os
import base64
from pathlib import Path
import httpx
import websockets

# Manual .env loading
try:
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
except Exception as e:
    print(f"[WARN] .env loading: {e}")

# Configuration
ASTERISK_HOST = os.getenv('ASTERISK_HOST', 'localhost')
ASTERISK_ARI_PORT = os.getenv('ASTERISK_ARI_PORT', '8088')
ASTERISK_ARI_USER = 'python_ai'
ASTERISK_ARI_PASSWORD = 'python_ai_secret'

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

print(f"[INIT] Asterisk ARI: {ASTERISK_HOST}:{ASTERISK_ARI_PORT}")
print(f"[INIT] OpenAI API key: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'NOT SET'}...")


class ARIRealtimeHandler:
    """Real-time обработка звонков через Asterisk ARI + OpenAI"""
    
    def __init__(self):
        self.ari_ws = None
        self.openai_ws = None
        self.active_channels = {}
        
    async def connect_ari(self):
        """Подключение к Asterisk ARI WebSocket"""
        ari_url = f"ws://{ASTERISK_HOST}:{ASTERISK_ARI_PORT}/ari/events"
        ari_url += f"?app=realtime_ai&api_key={ASTERISK_ARI_USER}:{ASTERISK_ARI_PASSWORD}"
        
        print(f"[ARI] Connecting to {ari_url}")
        
        try:
            self.ari_ws = await websockets.connect(ari_url)
            print("[ARI] Connected to Asterisk")
            return True
        except Exception as e:
            print(f"[ARI] Connection error: {e}")
            return False
            
    async def connect_openai(self):
        """Подключение к OpenAI Realtime API"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        try:
            self.openai_ws = await websockets.connect(
                OPENAI_REALTIME_URL,
                extra_headers=headers
            )
            
            # Конфигурация сессии
            config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "Ты - AI ассистент call-центра. Поздоровайся с клиентом и спроси чем можешь помочь. Определи отдел: sales, support или billing. Будь очень краток.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 700
                    }
                }
            }
            
            await self.openai_ws.send(json.dumps(config))
            print("[OPENAI] Connected to Realtime API")
            return True
            
        except Exception as e:
            print(f"[OPENAI] Connection error: {e}")
            return False
            
    async def handle_channel(self, channel_id: str, caller_number: str):
        """
        Обработка канала в real-time
        """
        print(f"[CHANNEL] Handling {channel_id} from {caller_number}")
        
        # Подключаемся к OpenAI
        if not await self.connect_openai():
            return
            
        try:
            # Создаём external media channel для получения аудио
            async with httpx.AsyncClient() as client:
                # Создаём snoop для получения аудио
                snoop_url = f"http://{ASTERISK_HOST}:{ASTERISK_ARI_PORT}/ari/channels/{channel_id}/snoop"
                auth = (ASTERISK_ARI_USER, ASTERISK_ARI_PASSWORD)
                
                params = {
                    "spy": "in",  # Получаем входящее аудио
                    "whisper": "out",  # Отправляем исходящее аудио
                    "app": "realtime_ai",
                    "snoopId": f"snoop-{channel_id}"
                }
                
                response = await client.post(snoop_url, auth=auth, params=params)
                
                if response.status_code == 200:
                    snoop_data = response.json()
                    print(f"[SNOOP] Created: {snoop_data}")
                    
                    # TODO: Получаем RTP поток и стримим в OpenAI
                    # Это требует дополнительной настройки external media
                    
                else:
                    print(f"[SNOOP] Error {response.status_code}: {response.text}")
                    
        except Exception as e:
            print(f"[ERROR] Channel handling: {e}")
        finally:
            if self.openai_ws:
                await self.openai_ws.close()
                
    async def listen_events(self):
        """Прослушивание событий из Asterisk ARI"""
        if not await self.connect_ari():
            return
            
        print("[ARI] Listening for events...")
        
        try:
            async for message in self.ari_ws:
                try:
                    event = json.loads(message)
                    event_type = event.get('type')
                    
                    if event_type == 'StasisStart':
                        # Новый звонок
                        channel = event.get('channel', {})
                        channel_id = channel.get('id')
                        caller_number = channel.get('caller', {}).get('number', 'unknown')
                        
                        print(f"[EVENT] StasisStart: {channel_id} from {caller_number}")
                        
                        # Обрабатываем канал в отдельной задаче
                        asyncio.create_task(self.handle_channel(channel_id, caller_number))
                        
                    elif event_type == 'StasisEnd':
                        # Звонок завершён
                        channel_id = event.get('channel', {}).get('id')
                        print(f"[EVENT] StasisEnd: {channel_id}")
                        
                    else:
                        print(f"[EVENT] {event_type}")
                        
                except Exception as e:
                    print(f"[ERROR] Event processing: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("[ARI] Connection closed")
        except Exception as e:
            print(f"[ERROR] ARI listener: {e}")
            
    async def run(self):
        """Запуск обработчика"""
        print("[REALTIME] Starting ARI Real-time handler...")
        await self.listen_events()


async def main():
    """Main entry point"""
    handler = ARIRealtimeHandler()
    await handler.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[REALTIME] Shutting down...")

