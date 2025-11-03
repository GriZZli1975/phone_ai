#!/usr/bin/env python3
"""
AudioSocket Server для real-time streaming Asterisk ↔ ElevenLabs
Asterisk передаёт аудио через TCP на порт 9092
"""
import asyncio
import struct
import uuid
import sys
import time
import numpy as np
from scipy import signal
from pathlib import Path
import os
import audioop

# Unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)


def resample_8k_to_16k(audio_8k: bytes) -> bytes:
    """
    Конвертация PCM16 8kHz → 16kHz для ElevenLabs
    """
    # Конвертируем bytes → numpy array
    audio_array = np.frombuffer(audio_8k, dtype=np.int16)
    
    # Resample 8000 → 16000 Hz (увеличиваем в 2 раза)
    resampled = signal.resample(audio_array, len(audio_array) * 2)
    
    # Конвертируем обратно в int16
    resampled_int16 = resampled.astype(np.int16)
    
    return resampled_int16.tobytes()


def resample_16k_to_8k(audio_16k: bytes) -> bytes:
    """
    Конвертация PCM16 16kHz → 8kHz для Asterisk
    """
    # Конвертируем bytes → numpy array
    audio_array = np.frombuffer(audio_16k, dtype=np.int16)
    
    # Resample 16000 → 8000 Hz (уменьшаем в 2 раза)
    resampled = signal.resample(audio_array, len(audio_array) // 2)
    
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


SPEECH_RMS_THRESHOLD = int(os.getenv("ELEVENLABS_SPEECH_THRESHOLD", "300"))
SILENCE_TIMEOUT = float(os.getenv("ELEVENLABS_SILENCE_TIMEOUT", "0.8"))


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
            stream_task = asyncio.create_task(
                elevenlabs.stream_responses()
            )
            
            # Ждём завершения ВСЕХ задач (полный диалог)
            await asyncio.gather(receive_task, send_task, stream_task, return_exceptions=True)
            
            print("[AUDIOSOCKET] Conversation cycle completed")
                
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
            # Первый фрейм - UUID (тип 0x01)
            uuid_header = await reader.readexactly(3)
            uuid_type, uuid_len = struct.unpack('!BH', uuid_header)
            
            if uuid_type == 0x01:  # UUID frame
                uuid_bytes = await reader.readexactly(uuid_len)
                # UUID - это 16 байт в hex формате, не UTF-8 строка
                uuid_hex = uuid_bytes.hex()
                print(f"[AUDIOSOCKET] Received UUID: {uuid_hex} ({uuid_len} bytes)")
            else:
                print(f"[AUDIOSOCKET] WARNING: Expected UUID type 0x01, got {uuid_type:02x}")
            
            print("[AUDIOSOCKET] Now reading audio frames...")
            
            speaking = False
            last_voice_ts = time.monotonic()

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
                    
                    # Читаем энергетику, чтобы убедиться что аудио не пустое
                    try:
                        rms = audioop.rms(audio_data, 2)
                    except Exception:
                        rms = 0

                    # Конвертируем PCM16 8kHz → μ-law 8kHz
                    try:
                        ulaw_payload = audioop.lin2ulaw(audio_data, 2)
                        await elevenlabs.send_audio(ulaw_payload)
                        if frame_count <= 5 or frame_count % 50 == 0:
                            print(
                                f"[ELEVEN] Sent audio chunk #{frame_count}: "
                                f"{len(ulaw_payload)} bytes (PCM16→μ-law, rms={rms})"
                            )
                    except Exception as e:
                        print(f"[ELEVEN] Error converting/sending audio: {e}")

                    now = time.monotonic()
                    if rms >= SPEECH_RMS_THRESHOLD:
                        if not speaking:
                            speaking = True
                            print(f"[AUDIOSOCKET] Voice detected, rms={rms}")
                        last_voice_ts = now
                    else:
                        if speaking and (now - last_voice_ts) >= SILENCE_TIMEOUT:
                            speaking = False
                            try:
                                await elevenlabs.end_user_turn()
                                print(
                                    f"[ELEVEN] Sent user_activity after {frame_count} frames "
                                    f"(silence {now - last_voice_ts:.2f}s)"
                                )
                            except Exception as e:
                                print(f"[ELEVEN] Error sending end_user_turn: {e}")
                    
                elif frame_type == 0x00:  # Hangup
                    print(f"[AUDIOSOCKET] Hangup signal received after {frame_count} frames")
                    # Сигнализируем ElevenLabs что пользователь закончил
                    await elevenlabs.end_user_turn()
                    print("[AUDIOSOCKET] Sent user_audio_done to ElevenLabs")
                    break
                else:
                    print(f"[AUDIOSOCKET] Unknown frame type: {frame_type:02x} (expected 0x10 for audio)")
                    
            # Когда цикл завершился, сигнализируем конец (если не было hangup)
            if frame_count > 0:
                print(f"[AUDIOSOCKET] Total frames received: {frame_count}")
                await elevenlabs.end_user_turn()
                print("[AUDIOSOCKET] Waiting for ElevenLabs response...")
                    
        except asyncio.IncompleteReadError:
            print(f"[AUDIOSOCKET] Connection closed by Asterisk (received {frame_count} frames)")
        except Exception as e:
            print(f"[AUDIOSOCKET] Receive error: {e} (received {frame_count} frames)")
            
    async def send_to_asterisk(self, writer, elevenlabs: ElevenLabsConvAI):
        """
        Получение аудио из очереди и отправка в Asterisk в реальном времени
        """
        print("[AUDIOSOCKET] Started sending to Asterisk (streaming mode)")
        
        total_sent = 0
        chunks_sent = 0
        chunk_size = 160  # 20ms μ-law @8kHz
        
        try:
            while True:
                # Читаем следующий чанк из очереди
                audio_chunk = await elevenlabs.audio_queue.get()
                
                # None = конец ответа агента
                if audio_chunk is None:
                    print(f"[AUDIOSOCKET] ✅ Agent response sent: {total_sent} bytes in {chunks_sent} frames")
                    total_sent = 0
                    chunks_sent = 0
                    continue
                
                # Разбиваем большой чанк на мелкие кадры
                for offset in range(0, len(audio_chunk), chunk_size):
                    frame_data = audio_chunk[offset:offset+chunk_size]
                    if len(frame_data) < chunk_size:
                        frame_data = frame_data.ljust(chunk_size, b'\xff')
                    
                    # AudioSocket audio frame: 0x10 + length + data
                    frame = struct.pack('!BH', 0x10, len(frame_data)) + frame_data
                    writer.write(frame)
                    await writer.drain()
                    
                    total_sent += len(frame_data)
                    chunks_sent += 1
                    
                    # Минимальная задержка только для drain()
                    # await asyncio.sleep(0.001)  # можно раскомментировать при проблемах
                    
                    if chunks_sent <= 5 or chunks_sent % 50 == 0:
                        print(f"[AUDIOSOCKET] ⬅️ Sent frame #{chunks_sent}: {len(frame_data)} bytes")
            
        except Exception as e:
            print(f"[AUDIOSOCKET] Send error: {e}")
            import traceback
            traceback.print_exc()
            
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

