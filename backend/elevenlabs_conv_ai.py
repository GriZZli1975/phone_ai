#!/usr/bin/env python3
"""
ElevenLabs Conversational AI integration
Real-time voice agent через WebSocket
"""
import asyncio
import json
import os
import base64
from pathlib import Path
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
    print("[INIT] Loaded .env for ElevenLabs Conv AI")
except Exception as e:
    print(f"[WARN] .env loading: {e}")

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', 'your-agent-id')

# ElevenLabs Conversational AI WebSocket endpoint
ELEVENLABS_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation"

print(f"[INIT] ElevenLabs API key: {ELEVENLABS_API_KEY[:20] if ELEVENLABS_API_KEY else 'NOT SET'}...")
print(f"[INIT] Agent ID: {ELEVENLABS_AGENT_ID}")


class ElevenLabsConvAI:
    """
    ElevenLabs Conversational AI handler
    Real-time voice conversation через WebSocket
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or ELEVENLABS_AGENT_ID
        self.ws = None
        self.conversation_id = None
        
    async def connect(self):
        """Подключение к ElevenLabs Conversational AI"""
        try:
            # Формируем URL с API ключом
            url = f"{ELEVENLABS_WS_URL}?agent_id={self.agent_id}"
            
            headers = {
                "xi-api-key": ELEVENLABS_API_KEY
            }
            
            print(f"[ELEVEN] Connecting to Conversational AI...")
            
            self.ws = await websockets.connect(url, extra_headers=headers)
            
            print("[ELEVEN] ✅ Connected to ElevenLabs Conversational AI")
            
            # Получаем приветственное сообщение
            welcome = await self.ws.recv()
            welcome_data = json.loads(welcome)
            
            if welcome_data.get('type') == 'conversation_initiation_metadata':
                self.conversation_id = welcome_data.get('conversation_id')
                print(f"[ELEVEN] Conversation ID: {self.conversation_id}")
            
            return True
            
        except Exception as e:
            print(f"[ELEVEN] ❌ Connection error: {e}")
            return False
            
    async def send_audio(self, audio_chunk: bytes):
        """
        Отправка аудио чанка в ElevenLabs
        audio_chunk: PCM16 8kHz mono audio data
        """
        if not self.ws:
            await self.connect()
        
        # Кодируем в base64
        audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
        
        message = {
            "type": "audio",
            "audio": audio_base64
        }
        
        await self.ws.send(json.dumps(message))
        
    async def end_user_turn(self):
        """Сигнализируем что пользователь закончил говорить"""
        message = {
            "type": "user_audio_done"
        }
        await self.ws.send(json.dumps(message))
        
    async def receive_response(self):
        """
        Получение ответа от ElevenLabs
        Возвращает: (text, audio_chunks, is_final)
        """
        text = ""
        audio_chunks = []
        
        try:
            while True:
                message = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
                data = json.loads(message)
                
                msg_type = data.get('type')
                
                if msg_type == 'audio':
                    # Получили аудио чанк
                    audio_base64 = data.get('audio', '')
                    if audio_base64:
                        audio_data = base64.b64decode(audio_base64)
                        audio_chunks.append(audio_data)
                        
                elif msg_type == 'transcript':
                    # Получили текст ответа
                    text = data.get('text', '')
                    print(f"[ELEVEN] Agent says: {text}")
                    
                elif msg_type == 'agent_response_end':
                    # Агент закончил отвечать
                    print("[ELEVEN] Agent response complete")
                    break
                    
                elif msg_type == 'error':
                    print(f"[ELEVEN] Error: {data}")
                    break
                    
        except asyncio.TimeoutError:
            print("[ELEVEN] Timeout waiting for response")
            
        return text, audio_chunks
        
    async def close(self):
        """Закрытие соединения"""
        if self.ws:
            await self.ws.close()
            print("[ELEVEN] Connection closed")


async def test_elevenlabs_conv_ai():
    """Тестирование ElevenLabs Conversational AI"""
    agent = ElevenLabsConvAI()
    
    if not await agent.connect():
        print("[TEST] Failed to connect")
        return
    
    # Симуляция отправки аудио
    print("[TEST] Sending test audio...")
    dummy_audio = b'\x00\x00' * 8000  # 1 секунда тишины
    await agent.send_audio(dummy_audio)
    await agent.end_user_turn()
    
    # Получаем ответ
    print("[TEST] Waiting for response...")
    text, audio = await agent.receive_response()
    
    print(f"[TEST] Response text: {text}")
    print(f"[TEST] Response audio chunks: {len(audio)}")
    
    await agent.close()


if __name__ == '__main__':
    asyncio.run(test_elevenlabs_conv_ai())

