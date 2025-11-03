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
        self.audio_queue = None
        
    async def connect(self):
        """Подключение к ElevenLabs Conversational AI"""
        try:
            self.audio_queue = asyncio.Queue()
            
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
            
            print(f"[ELEVEN] Welcome message: {welcome[:100]}...")
            
            if welcome_data.get('type') == 'conversation_initiation_metadata':
                metadata = welcome_data.get('conversation_initiation_metadata_event', {})
                self.conversation_id = metadata.get('conversation_id')
                audio_format = metadata.get('user_input_audio_format')
                print(f"[ELEVEN] Conversation ID: {self.conversation_id}")
                print(f"[ELEVEN] Audio format: {audio_format}")
            
            return True
            
        except Exception as e:
            print(f"[ELEVEN] ❌ Connection error: {e}")
            return False
            
    async def send_audio(self, audio_chunk: bytes):
        """
        Отправка аудио чанка в ElevenLabs
        audio_chunk: PCM audio data (μ-law 8kHz для телефонии)
        """
        if not self.ws:
            await self.connect()
        
        # Кодируем в base64
        audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
        
        # Правильный формат по документации:
        # https://elevenlabs.io/docs/agents-platform/api-reference/agents-platform/websocket
        message = {
            "user_audio_chunk": audio_base64
        }
        
        await self.ws.send(json.dumps(message))
        
    async def end_user_turn(self):
        """Сигнализируем что пользователь закончил говорить"""
        # По документации: user_activity для сигнала активности
        message = {
            "type": "user_activity"
        }
        await self.ws.send(json.dumps(message))
        
    async def stream_responses(self):
        """
        Постоянный стрим событий от ElevenLabs
        Аудио кладётся в очередь для немедленной отправки
        """
        if not self.ws:
            print("[ELEVEN] stream_responses called without active websocket")
            return

        chunk_count = 0

        try:
            while True:
                message = await self.ws.recv()
                data = json.loads(message)

                msg_type = data.get('type')

                if msg_type == 'audio':
                    audio_event = data.get('audio_event', {})
                    audio_base64 = audio_event.get('audio_base_64', '')
                    if audio_base64:
                        audio_data = base64.b64decode(audio_base64)
                        chunk_count += 1
                        await self.audio_queue.put(audio_data)
                        print(f"[ELEVEN] 🔊 Agent audio chunk #{chunk_count}: {len(audio_data)} bytes → queued")

                elif msg_type == 'agent_response':
                    agent_response_event = data.get('agent_response_event', {})
                    response_text = agent_response_event.get('agent_response', '')
                    if response_text:
                        print(f"[ELEVEN] Agent says: {response_text}")

                elif msg_type == 'agent_response_end':
                    print(f"[ELEVEN] Agent response complete: {chunk_count} audio chunks")
                    await self.audio_queue.put(None)
                    chunk_count = 0

                elif msg_type == 'user_transcript':
                    user_event = data.get('user_transcription_event', {})
                    user_text = user_event.get('user_transcript', '')
                    if user_text:
                        print(f"[ELEVEN] 👤 USER said: {user_text}")

                elif msg_type == 'vad_score':
                    vad_event = data.get('vad_score_event', {})
                    vad_value = vad_event.get('vad_score', 0)
                    if vad_value > 0.3:
                        print(f"[ELEVEN] 🎤 VAD: {vad_value:.2f}")

                elif msg_type == 'ping':
                    ping_event = data.get('ping_event', {})
                    event_id = ping_event.get('event_id')
                    if event_id:
                        await self.ws.send(json.dumps({"type": "pong", "event_id": event_id}))

                elif msg_type == 'error':
                    print(f"[ELEVEN] Error: {data}")
                    await self.audio_queue.put(None)
                    break

        except websockets.ConnectionClosed as exc:
            print(f"[ELEVEN] Connection closed: {exc}")
            await self.audio_queue.put(None)
        
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

