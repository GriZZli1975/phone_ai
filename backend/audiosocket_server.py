#!/usr/bin/env python3
"""
AudioSocket Server для real-time streaming Asterisk ↔ ElevenLabs
Asterisk передаёт аудио через TCP на порт 9092
"""
import asyncio
import struct
import uuid
from pathlib import Path
import os

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
            # Читаем UUID от Asterisk (первые 3 байта: тип + длина)
            header = await reader.readexactly(3)
            msg_type, uuid_len = struct.unpack('!BH', header)
            
            if msg_type == 0x00:  # UUID message
                uuid_bytes = await reader.readexactly(uuid_len)
                received_uuid = uuid_bytes.decode('utf-8')
                print(f"[AUDIOSOCKET] Received UUID: {received_uuid}")
            else:
                print(f"[AUDIOSOCKET] Unexpected message type: {msg_type}")
                writer.close()
                await writer.wait_closed()
                return
            
            # Задачи для двустороннего стриминга
            receive_task = asyncio.create_task(
                self.receive_from_asterisk(reader, elevenlabs)
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
            
    async def receive_from_asterisk(self, reader, elevenlabs: ElevenLabsConvAI):
        """
        Получение аудио от Asterisk и отправка в ElevenLabs
        """
        print("[AUDIOSOCKET] Started receiving from Asterisk")
        
        try:
            while True:
                # AudioSocket фрейм: 3 байта header + аудио данные
                # Header: 1 байт тип (0x10=audio), 2 байта длина
                header = await reader.readexactly(3)
                
                if not header:
                    break
                    
                frame_type, length = struct.unpack('!BH', header)
                
                if frame_type == 0x10:  # Audio frame
                    # Читаем аудио данные
                    audio_data = await reader.readexactly(length)
                    
                    # Отправляем в ElevenLabs
                    await elevenlabs.send_audio(audio_data)
                    
                elif frame_type == 0x00:  # Hangup
                    print("[AUDIOSOCKET] Hangup signal received")
                    await elevenlabs.end_user_turn()
                    break
                    
        except asyncio.IncompleteReadError:
            print("[AUDIOSOCKET] Connection closed by Asterisk")
        except Exception as e:
            print(f"[AUDIOSOCKET] Receive error: {e}")
            
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
        server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )
        
        addr = server.sockets[0].getsockname()
        print(f"[AUDIOSOCKET] Listening on {addr}")
        
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

