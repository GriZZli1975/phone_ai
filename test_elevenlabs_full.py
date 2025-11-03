#!/usr/bin/env python3
"""
Полный тест ElevenLabs Conversational AI:
1. Подключение
2. Отправка аудио
3. Получение ответа
"""
import asyncio
import websockets
import json
import base64
import numpy as np

# Ваши данные
ELEVENLABS_API_KEY = "sk_512ac30cd15ba2a71d54f959e52ab0cecee8b840d3cad6be"
ELEVENLABS_AGENT_ID = "agent_9201k94gqz14etxtrtxmna8w7szy"

ELEVENLABS_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation"


async def test_full_conversation():
    """Полный тест разговора с ElevenLabs"""
    
    print("=" * 60)
    print("ТЕСТ: ElevenLabs Conversational AI")
    print("=" * 60)
    
    # Подключение
    url = f"{ELEVENLABS_WS_URL}?agent_id={ELEVENLABS_AGENT_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    print(f"\n1. Подключение к ElevenLabs...")
    
    try:
        async with websockets.connect(url, extra_headers=headers) as ws:
            print("✅ WebSocket подключён!")
            
            # Получаем welcome message
            print("\n2. Получение welcome message...")
            welcome = await asyncio.wait_for(ws.recv(), timeout=5.0)
            welcome_data = json.loads(welcome)
            
            print(f"   Type: {welcome_data.get('type')}")
            
            if 'conversation_initiation_metadata_event' in welcome_data:
                metadata = welcome_data['conversation_initiation_metadata_event']
                print(f"   Conversation ID: {metadata.get('conversation_id')}")
                print(f"   Input format: {metadata.get('user_input_audio_format')}")
                print(f"   Output format: {metadata.get('agent_output_audio_format')}")
            
            # Генерируем тестовое аудио (1 секунда тишины в PCM16 16kHz)
            print("\n3. Отправка тестового аудио (1 сек тишины)...")
            
            # PCM16 16000 Hz = 16000 samples/sec * 2 bytes = 32000 bytes/sec
            # 1 секунда = 32000 байт
            test_audio = np.zeros(16000, dtype=np.int16)
            audio_bytes = test_audio.tobytes()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Отправляем чанками по 160ms (~5120 байт)
            chunk_size = 5120
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                
                message = {
                    "type": "audio",
                    "audio": chunk_b64
                }
                
                await ws.send(json.dumps(message))
                await asyncio.sleep(0.16)  # 160ms между чанками
            
            print(f"   Отправлено {len(audio_bytes)} bytes в {len(audio_bytes)//chunk_size + 1} чанках")
            
            # Сигнализируем конец речи
            print("\n4. Отправка user_audio_done...")
            await ws.send(json.dumps({"type": "user_audio_done"}))
            
            # Получаем ответ
            print("\n5. Получение ответа от агента...")
            
            response_text = ""
            audio_chunks = []
            
            timeout_count = 0
            while timeout_count < 10:  # Максимум 10 секунд ожидания
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    
                    msg_type = data.get('type')
                    
                    if msg_type == 'audio':
                        print(f"   Получено: type={msg_type}")
                        # Правильная структура: audio_event.audio_base_64
                        audio_event = data.get('audio_event', {})
                        audio_b64 = audio_event.get('audio_base_64', '')
                        if audio_b64:
                            audio_chunk = base64.b64decode(audio_b64)
                            audio_chunks.append(audio_chunk)
                            print(f"   ✅ Извлечено {len(audio_chunk)} bytes аудио")
                            
                    elif msg_type == 'agent_response':
                        print(f"   Получено: type=agent_response")
                        # Правильная структура: agent_response_event.agent_response
                        agent_event = data.get('agent_response_event', {})
                        text_content = agent_event.get('agent_response', '')
                        if text_content:
                            response_text += text_content
                            print(f"   ✅ Текст: {text_content}")
                        
                    elif msg_type == 'transcript':
                        text = data.get('text', '')
                        response_text += text
                        print(f"   Транскрипт: {text}")
                        
                    elif msg_type == 'agent_response_end':
                        print("   ✅ Агент закончил отвечать")
                        break
                        
                    elif msg_type == 'ping':
                        # Игнорируем ping
                        pass
                        
                    elif msg_type == 'error':
                        print(f"   ❌ Ошибка: {data}")
                        break
                    else:
                        print(f"   Получено: type={msg_type}")
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    
            print(f"\n6. Результат:")
            print(f"   Текст ответа: {response_text or 'нет текста'}")
            print(f"   Аудио чанков: {len(audio_chunks)}")
            print(f"   Общий размер аудио: {sum(len(c) for c in audio_chunks)} bytes")
            
            if audio_chunks:
                print("\n✅ УСПЕХ! ElevenLabs ответил голосом!")
            else:
                print("\n⚠️  Ответ получен, но без аудио")
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_full_conversation())

