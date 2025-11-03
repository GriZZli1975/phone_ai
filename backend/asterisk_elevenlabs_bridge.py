#!/usr/bin/env python3
"""
Asterisk <-> ElevenLabs Conversational AI Bridge
Real-time audio streaming между Asterisk и ElevenLabs
"""
import asyncio
import socket
import struct
from elevenlabs_conv_ai import ElevenLabsConvAI

# Asterisk External Media передаёт RTP напрямую
# Формат: PCM16, 8000 Hz, mono

class AsteriskElevenLabsBridge:
    """
    Мост между Asterisk RTP и ElevenLabs WebSocket
    """
    
    def __init__(self, rtp_port: int = 10000):
        self.rtp_port = rtp_port
        self.elevenlabs = ElevenLabsConvAI()
        self.rtp_socket = None
        
    async def start_rtp_listener(self):
        """Запуск RTP listener для получения аудио от Asterisk"""
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_socket.bind(('0.0.0.0', self.rtp_port))
        self.rtp_socket.setblocking(False)
        
        print(f"[RTP] Listening on port {self.rtp_port}")
        
    async def bridge_call(self):
        """
        Мост для звонка: RTP → ElevenLabs → RTP
        """
        # Подключаемся к ElevenLabs
        if not await self.elevenlabs.connect():
            return
        
        print("[BRIDGE] Starting audio bridge...")
        
        try:
            # Задача 1: Получение RTP от Asterisk → отправка в ElevenLabs
            asyncio.create_task(self.rtp_to_elevenlabs())
            
            # Задача 2: Получение ответа от ElevenLabs → отправка в Asterisk RTP
            asyncio.create_task(self.elevenlabs_to_rtp())
            
            # Держим соединение
            await asyncio.sleep(60)  # Максимум 60 секунд на звонок
            
        finally:
            await self.elevenlabs.close()
            if self.rtp_socket:
                self.rtp_socket.close()
                
    async def rtp_to_elevenlabs(self):
        """Получение RTP от Asterisk и отправка в ElevenLabs"""
        print("[BRIDGE] RTP → ElevenLabs started")
        
        while True:
            try:
                # Получаем RTP пакет (неблокирующе)
                await asyncio.sleep(0.02)  # 20ms
                
                try:
                    data, addr = self.rtp_socket.recvfrom(2048)
                except BlockingIOError:
                    continue
                
                # Парсим RTP пакет
                if len(data) < 12:
                    continue
                    
                # RTP header: 12 байт, дальше идёт payload
                payload = data[12:]
                
                # Отправляем аудио в ElevenLabs
                await self.elevenlabs.send_audio(payload)
                
            except Exception as e:
                print(f"[BRIDGE] RTP error: {e}")
                break
                
    async def elevenlabs_to_rtp(self):
        """Получение ответа от ElevenLabs и отправка в Asterisk RTP"""
        print("[BRIDGE] ElevenLabs → RTP started")
        
        text, audio_chunks = await self.elevenlabs.receive_response()
        
        print(f"[BRIDGE] Got response: {len(audio_chunks)} chunks")
        
        # TODO: Отправка аудио обратно в Asterisk через RTP
        # Это требует создания RTP пакетов с правильными заголовками
        

async def main():
    """Тест моста"""
    bridge = AsteriskElevenLabsBridge(port=10000)
    await bridge.start_rtp_listener()
    await bridge.bridge_call()


if __name__ == '__main__':
    asyncio.run(main())

