#!/usr/bin/env python3
"""
Real-time AGI handler с OpenAI Realtime API
Без записи файлов - прямой стриминг аудио
"""
import asyncio
import socket
import json
import base64
import os
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
    print("[INIT] Loaded .env for realtime AGI")
except Exception as e:
    print(f"[WARN] .env loading: {e}")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

print(f"[INIT] OpenAI API key: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'NOT SET'}...")


class AGISession:
    """AGI session handler"""
    
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.agi_vars = {}
        
    async def read_agi_env(self):
        """Read AGI environment variables"""
        print("[AGI] Reading environment...")
        while True:
            line = await self.reader.readline()
            line = line.decode('utf-8').strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                self.agi_vars[key.strip()] = value.strip()
        print(f"[AGI] Environment loaded: {len(self.agi_vars)} vars")
        
    async def send_command(self, command):
        """Send AGI command"""
        self.writer.write(f"{command}\n".encode('utf-8'))
        await self.writer.drain()
        
        response = await self.reader.readline()
        response = response.decode('utf-8').strip()
        return response
        
    async def verbose(self, message):
        """Send verbose message"""
        await self.send_command(f'VERBOSE "{message}" 1')
        
    async def answer(self):
        """Answer call"""
        return await self.send_command('ANSWER')
        
    async def hangup(self):
        """Hangup call"""
        return await self.send_command('HANGUP')
        
    async def stream_file(self, file_path):
        """Stream audio file"""
        return await self.send_command(f'STREAM FILE {file_path} ""')


async def handle_realtime_call(session: AGISession, call_id: str):
    """
    Real-time обработка звонка через OpenAI Realtime API
    """
    await session.verbose(f"Real-time AI Call Handler for {call_id}")
    
    # Подключаемся к OpenAI Realtime API
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }
    
    try:
        async with websockets.connect(OPENAI_REALTIME_URL, extra_headers=headers) as ws:
            print(f"[REALTIME] Connected to OpenAI for call {call_id}")
            
            # Конфигурация сессии
            config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "Ты - AI ассистент call-центра. Поздоровайся с клиентом и спроси чем можешь помочь. Определи отдел: sales (продажи), support (техподдержка) или billing (бухгалтерия). Будь очень краток и дружелюбен.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "silence_duration_ms": 800
                    }
                }
            }
            
            await ws.send(json.dumps(config))
            await session.verbose("OpenAI Realtime API connected")
            
            # TODO: Здесь нужно получать аудио chunks от Asterisk
            # и отправлять в OpenAI, а ответ возвращать обратно
            
            # Пока просто ждём и вешаем трубку
            await asyncio.sleep(10)
            
    except Exception as e:
        print(f"[REALTIME] Error: {e}")
        await session.verbose(f"Error: {e}")


async def handle_agi_client(reader, writer):
    """Обработка AGI клиента"""
    addr = writer.get_extra_info('peername')
    print(f"[AGI] New connection from {addr}")
    
    try:
        session = AGISession(reader, writer)
        await session.read_agi_env()
        
        call_id = session.agi_vars.get('agi_arg_1', 'unknown')
        
        # Real-time обработка
        await handle_realtime_call(session, call_id)
        
    except Exception as e:
        print(f"[ERROR] AGI session: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[AGI] Connection closed: {addr}")


async def main():
    """Запуск FastAGI сервера"""
    print("[AGI-REALTIME] Starting FastAGI server on 0.0.0.0:4573...")
    
    server = await asyncio.start_server(
        handle_agi_client,
        '0.0.0.0',
        4573
    )
    
    addr = server.sockets[0].getsockname()
    print(f"[AGI-REALTIME] Listening on {addr}")
    
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[AGI-REALTIME] Shutting down...")

