#!/usr/bin/env python3
"""
AudioSocket Server для real-time streaming Asterisk ↔ ElevenLabs
Asterisk передаёт аудио через TCP на порт 9092
"""
import asyncio
import struct
import uuid
import sys
import numpy as np
from scipy import signal
from pathlib import Path
import os

# Unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)


def resample_8k_to_16k(audio_8k: bytes) -> bytes:
    """
    Конвертация PCM16 8kHz → 16kHz для ElevenLabs
    """
    # Конвертируем bytes → numpy array
    audio_array = np.frombuffer(audio_8k, dtype=np.int16)
    
    # Resample 8000 → 16000 Hz
    resampled = signal.resample(audio_array, len(audio_array) * 2)
    
    # Конвертируем обратно в int16
    resampled_int16 = resampled.astype(np.int16)
    
    return resampled_int16.tobytes()

# Manual .env loading
try:
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print("[INIT] Loaded .env for AudioSocket")
except Exception as e:
    print(f"[WARN] .env loading: {e}")

# Импортируем ElevenLabs Conversational AI
from elevenlabs_conv_ai import ElevenLabsConvAI


class AudioSocketServer:
    """
    AudioSocket сервер для приёма аудио от Asterisk
    Формат: slin16 (PCM 16-bit signed linear, 8000 Hz, mono)
    """
    
    def __init__(self, host='0.0.0.0', port=9092):
        self.host = host
        self.port = port
        
    async def handle_connection(self, reader, writer):
        """Обработка подключения от Asterisk"""
        addr = writer.get_extra_info('peername')
        call_id = str(uuid.uuid4())
        
        print(f"[AUDIOSOCKET] New connection from {addr}, call_id: {call_id}")
        
        # Создаём ElevenLabs агента
        elevenlabs = ElevenLabsConvAI()
        
        if not await elevenlabs.connect():
            print("[AUDIOSOCKET] Failed to connect to ElevenLabs")
            writer.close()
            await writer.wait_closed()
            return
        
        try:
            # AudioSocket протокол не отправляет UUID первым
            # Сразу начинаем обработку аудио
            print(f"[AUDIOSOCKET] Starting audio processing...")
            
            # Задачи для двустороннего стриминга
            receive_task = asyncio.create_task(
                self.receive_from_asterisk(reader, writer, elevenlabs)
            )
            send_task = asyncio.create_task(
                self.send_to_asterisk(writer, elevenlabs)
            )
            
            # Ждём завершения любой задачи
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем незавершённые задачи
            for task in pending:
                task.cancel()
                
        except Exception as e:
            print(f"[AUDIOSOCKET] Error: {e}")
        finally:
            await elevenlabs.close()
            writer.close()
            await writer.wait_closed()
            print(f"[AUDIOSOCKET] Connection closed: {call_id}")
            
    async def receive_from_asterisk(self, reader, writer, elevenlabs: ElevenLabsConvAI):
        """
        Получение аудио от Asterisk и отправка в ElevenLabs
        """
        print("[AUDIOSOCKET] Started receiving from Asterisk")
        frame_count = 0
        
        try:
            # AudioSocket сразу отправляет аудио фреймы без UUID
            print("[AUDIOSOCKET] Reading audio frames...")
            
            while True:
                # Читаем аудио фреймы
                try:
                    header = await asyncio.wait_for(reader.readexactly(3), timeout=0.5)
                except asyncio.TimeoutError:
                    # Отправляем тишину чтобы держать соединение
                    silence = struct.pack('!BH', 0x10, 160) + (b'\x00' * 160)
                    writer.write(silence)
                    await writer.drain()
                    continue
                    
                if not header or len(header) < 3:
                    break
                    
                frame_type, length = struct.unpack('!BH', header)
                
                if frame_type == 0x10:  # Audio frame (0x10 = 16)
                    # Читаем аудио данные
                    audio_data = await reader.readexactly(length)
                    frame_count += 1
                    
                    if frame_count <= 5 or frame_count % 50 == 0:
                        print(f"[AUDIOSOCKET] Frame #{frame_count}: type={frame_type:02x}, len={length}, data={len(audio_data)} bytes")
                    
                    # Отправляем в ElevenLabs
                    await elevenlabs.send_audio(audio_data)
                    
                elif frame_type == 0x00:  # Hangup
                    print("[AUDIOSOCKET] Hangup signal received")
                    await elevenlabs.end_user_turn()
                    break
                else:
                    print(f"[AUDIOSOCKET] Unknown frame type: {frame_type:02x} (expected 0x10 for audio)")
                    
        except asyncio.IncompleteReadError:
            print(f"[AUDIOSOCKET] Connection closed by Asterisk (received {frame_count} frames)")
        except Exception as e:
            print(f"[AUDIOSOCKET] Receive error: {e} (received {frame_count} frames)")
            
    async def send_to_asterisk(self, writer, elevenlabs: ElevenLabsConvAI):
        """
        Получение ответа от ElevenLabs и отправка в Asterisk
        """
        print("[AUDIOSOCKET] Started sending to Asterisk")
        
        try:
            # Получаем ответ от ElevenLabs
            text, audio_chunks = await elevenlabs.receive_response()
            
            print(f"[AUDIOSOCKET] Got response: {len(audio_chunks)} chunks")
            
            # Отправляем каждый аудио чанк в Asterisk
            for chunk in audio_chunks:
                # AudioSocket audio frame: 0x10 + length + data
                frame = struct.pack('!BH', 0x10, len(chunk)) + chunk
                writer.write(frame)
                await writer.drain()
                
            print("[AUDIOSOCKET] Finished sending audio")
            
        except Exception as e:
            print(f"[AUDIOSOCKET] Send error: {e}")
            
    async def run(self):
        """Запуск сервера"""
        print(f"[AUDIOSOCKET] Starting server on {self.host}:{self.port}...")
        
        server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )
        
        addr = server.sockets[0].getsockname()
        print(f"[AUDIOSOCKET] ✅ Listening on {addr}")
        print(f"[AUDIOSOCKET] Waiting for Asterisk connections...")
        
        async with server:
            await server.serve_forever()


async def main():
    """Main entry point"""
    server = AudioSocketServer()
    await server.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[AUDIOSOCKET] Shutting down...")

