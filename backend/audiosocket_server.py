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
import audioop

# Unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)


def ulaw_to_pcm16(ulaw_data: bytes) -> bytes:
    """
    Конвертация μ-law → PCM16 (signed linear)
    """
    # audioop.ulaw2lin конвертирует μ-law в linear PCM
    # width=2 означает 16-bit (PCM16)
    return audioop.ulaw2lin(ulaw_data, 2)


def pcm16_to_ulaw(pcm_data: bytes) -> bytes:
    """
    Конвертация PCM16 → μ-law для Asterisk
    """
    # audioop.lin2ulaw конвертирует linear PCM в μ-law
    # width=2 означает 16-bit (PCM16)
    return audioop.lin2ulaw(pcm_data, 2)


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


class AudioSocketServer:
    """
    AudioSocket сервер для приёма аудио от Asterisk и проксирования в ElevenLabs
    Формат определяется самим агентом ElevenLabs (см. conversation_initiation_metadata)
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
            
            # Ждём завершения ОБЕИХ задач (полный диалог)
            await asyncio.gather(receive_task, send_task, return_exceptions=True)
            
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
                    
                    # Адаптивно приводим формат к ожидаемому ElevenLabs
                    try:
                        input_fmt = getattr(elevenlabs, "user_input_audio_format", None) or "mulaw_8000"

                        if input_fmt in ("mulaw_8000", "ulaw_8000"):
                            payload = audio_data
                        elif input_fmt == "pcm_8000":
                            payload = ulaw_to_pcm16(audio_data)
                        elif input_fmt == "pcm_16000":
                            pcm_data = ulaw_to_pcm16(audio_data)
                            payload = resample_8k_to_16k(pcm_data)
                        else:
                            payload = audio_data
                            print(f"[ELEVEN] WARN: Unsupported user_input_audio_format '{input_fmt}', forwarding raw bytes")

                        await elevenlabs.send_audio(payload)

                        if frame_count <= 5:
                            print(f"[ELEVEN] Sent audio chunk #{frame_count}: {len(audio_data)} bytes → format {input_fmt}")
                    except Exception as e:
                        print(f"[ELEVEN] Error sending audio: {e}")
                    
                elif frame_type == 0x00:  # Hangup
                    print(f"[AUDIOSOCKET] Hangup signal received after {frame_count} frames")
                    # Сигнализируем ElevenLabs что пользователь закончил
                    await elevenlabs.end_user_turn()
                    print("[AUDIOSOCKET] Sent user_activity to ElevenLabs")
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
        Получение ответа от ElevenLabs и отправка в Asterisk
        """
        print("[AUDIOSOCKET] Started sending to Asterisk")
        
        try:
            # Получаем ответ от ElevenLabs
            text, audio_chunks = await elevenlabs.receive_response()
            
            print(f"[AUDIOSOCKET] Got response: text='{text}', audio={len(audio_chunks)} chunks")
            
            if not audio_chunks:
                print("[AUDIOSOCKET] No audio to send back")
                return
                
            # Собираем все аудио вместе (в исходном формате агента)
            full_audio = b"".join(audio_chunks)
            output_fmt = getattr(elevenlabs, "agent_output_audio_format", None) or "pcm_16000"
            print(f"[AUDIOSOCKET] Total audio from ElevenLabs: {len(full_audio)} bytes ({output_fmt})")

            # Приводим ответ к μ-law 8kHz для Asterisk
            if output_fmt in ("mulaw_8000", "ulaw_8000"):
                audio_for_asterisk = full_audio
            elif output_fmt == "pcm_8000":
                audio_for_asterisk = pcm16_to_ulaw(full_audio)
            elif output_fmt == "pcm_16000":
                pcm_8k = resample_16k_to_8k(full_audio)
                audio_for_asterisk = pcm16_to_ulaw(pcm_8k)
            else:
                print(f"[AUDIOSOCKET] WARN: Unsupported agent_output_audio_format '{output_fmt}', fallback to pcm_16000 path")
                pcm_8k = resample_16k_to_8k(full_audio)
                audio_for_asterisk = pcm16_to_ulaw(pcm_8k)

            # Разбиваем на чанки по 160 байт (20ms μ-law @ 8kHz)
            chunk_size = 160
            total_sent = 0
            chunks_sent = 0

            for offset in range(0, len(audio_for_asterisk), chunk_size):
                chunk_ulaw = audio_for_asterisk[offset:offset + chunk_size]

                # AudioSocket audio frame: 0x10 + length + data
                frame = struct.pack('!BH', 0x10, len(chunk_ulaw)) + chunk_ulaw
                writer.write(frame)
                await writer.drain()

                total_sent += len(chunk_ulaw)
                chunks_sent += 1

                # Небольшая задержка между чанками (20ms)
                await asyncio.sleep(0.02)

                if chunks_sent <= 3 or chunks_sent % 20 == 0:
                    print(f"[AUDIOSOCKET] Sent chunk #{chunks_sent}: {len(chunk_ulaw)} bytes (μ-law)")

            print(f"[AUDIOSOCKET] ✅ Finished sending {total_sent} bytes in {chunks_sent} chunks to Asterisk")
            
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

