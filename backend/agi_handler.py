#!/usr/bin/env python3
"""
FastAGI Server для real-time обработки звонков с OpenAI/ElevenLabs
"""
import os
import socket
import asyncio
import json
from pathlib import Path
import soundfile as sf
import numpy as np
import httpx
from openai import OpenAI

# Manual .env loading
try:
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print("[INIT] Loaded .env manually")
except Exception as e:
    print(f"[WARN] Could not load .env: {e}")

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')

print(f"[INIT] OpenAI key: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'NOT SET'}...")
print(f"[INIT] ElevenLabs key: {ELEVENLABS_API_KEY[:20] if ELEVENLABS_API_KEY else 'NOT SET'}...")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
        print(f"[AGI] -> {command}")
        print(f"[AGI] <- {response}")
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
        
    async def playback(self, file_path):
        """Playback audio file"""
        return await self.send_command(f'EXEC Playback {file_path}')


async def speech_to_text(audio_path: str) -> str:
    """
    Преобразование аудио в текст через OpenAI Whisper
    """
    try:
        print(f"[STT] Processing: {audio_path}")
        
        if not os.path.exists(audio_path):
            print(f"[STT] File not found: {audio_path}")
            return ""
            
        file_size = os.path.getsize(audio_path)
        print(f"[STT] File size: {file_size} bytes")
        
        if file_size < 1000:
            print("[STT] File too small, likely empty")
            return ""
        
        with open(audio_path, 'rb') as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )
        
        text = transcript.text
        print(f"[STT] Result: {text}")
        return text
        
    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""


async def get_ai_response(text: str) -> str:
    """
    Получить ответ от OpenAI GPT
    """
    try:
        print(f"[AI] Processing: {text}")
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты — AI ассистент call-центра. Определи, в какой отдел нужно перевести звонок: sales (продажи), support (техподдержка), billing (бухгалтерия). Ответь только названием отдела."},
                {"role": "user", "content": text}
            ],
            max_tokens=50,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip().lower()
        print(f"[AI] Response: {result}")
        return result
        
    except Exception as e:
        print(f"[AI] Error: {e}")
        return "support"


async def text_to_speech(text: str, output_path: str) -> bool:
    """
    Преобразование текста в речь через ElevenLabs
    """
    try:
        print(f"[TTS] Generating speech: {text}")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"[TTS] Saved to: {output_path}")
                return True
            else:
                print(f"[TTS] Error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return False


async def handle_call(session: AGISession, call_id: str):
    """
    Обработка входящего звонка
    """
    try:
        await session.verbose(f"AI Call Handler started for call {call_id}")
        
        # Путь к записи
        audio_path = f"/recordings/call_{call_id}.wav"
        
        # Ждём пока файл появится
        for i in range(10):
            if os.path.exists(audio_path):
                break
            await asyncio.sleep(1)
        
        if not os.path.exists(audio_path):
            await session.verbose("Recording file not found")
            return
        
        # Распознаём речь
        text = await speech_to_text(audio_path)
        
        if not text:
            await session.verbose("No speech detected")
            await session.playback("goodbye")
            return
        
        await session.verbose(f"Recognized: {text}")
        
        # Получаем ответ от AI
        department = await get_ai_response(text)
        await session.verbose(f"Department: {department}")
        
        # Генерируем ответ
        response_text = f"Переводю вас в отдел {department}"
        response_mp3 = f"/recordings/response_{call_id}.mp3"
        response_wav = f"/recordings/response_{call_id}.wav"
        response_asterisk = f"/var/spool/asterisk/monitor/response_{call_id}"
        
        if await text_to_speech(response_text, response_mp3):
            # Конвертируем MP3 → WAV для Asterisk
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(response_mp3)
                audio = audio.set_frame_rate(8000).set_channels(1)
                audio.export(response_wav, format="wav")
                print(f"[TTS] Converted to WAV: {response_wav}")
                
                # Проигрываем WAV (без расширения)
                await session.playback(response_asterisk)
            except Exception as e:
                print(f"[TTS] Conversion error: {e}")
        
        # Здесь можно добавить перевод на оператора
        # await session.send_command(f'EXEC Dial PJSIP/{department}@trunk')
        
    except Exception as e:
        print(f"[ERROR] Call handling: {e}")
        await session.verbose(f"Error: {e}")


async def handle_agi_client(reader, writer):
    """
    Обработка подключения FastAGI клиента
    """
    addr = writer.get_extra_info('peername')
    print(f"[AGI] New connection from {addr}")
    
    try:
        session = AGISession(reader, writer)
        
        # Читаем AGI environment
        await session.read_agi_env()
        
        # Получаем call_id из аргументов
        call_id = session.agi_vars.get('agi_arg_1', 'unknown')
        
        # Обрабатываем звонок
        await handle_call(session, call_id)
        
    except Exception as e:
        print(f"[ERROR] AGI session: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[AGI] Connection closed: {addr}")


async def main():
    """
    Запуск FastAGI сервера
    """
    print("[AGI] Starting FastAGI server on 0.0.0.0:4573...")
    
    server = await asyncio.start_server(
        handle_agi_client,
        '0.0.0.0',
        4573
    )
    
    addr = server.sockets[0].getsockname()
    print(f"[AGI] Listening on {addr}")
    
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[AGI] Shutting down...")

