#!/usr/bin/env python3
"""
Упрощённый ARI обработчик с библиотекой ari-py
"""
import ari
import os
import asyncio
from pathlib import Path

# Manual .env loading
try:
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print("[INIT] Loaded .env")
except Exception as e:
    print(f"[WARN] .env loading: {e}")

ASTERISK_HOST = os.getenv('ASTERISK_HOST', '127.0.0.1')
ASTERISK_ARI_PORT = os.getenv('ASTERISK_ARI_PORT', '8088')
ASTERISK_ARI_USER = 'python_ai'
ASTERISK_ARI_PASSWORD = 'python_ai_secret'

print(f"[INIT] Connecting to ARI: http://{ASTERISK_HOST}:{ASTERISK_ARI_PORT}")

try:
    # Подключение к ARI
    client = ari.connect(
        f'http://{ASTERISK_HOST}:{ASTERISK_ARI_PORT}',
        ASTERISK_ARI_USER,
        ASTERISK_ARI_PASSWORD
    )
    
    print("[ARI] ✅ Connected!")
    
    def on_start(channel_obj, event):
        """Обработка входящего звонка"""
        channel_id = event['channel']['id']
        caller = event['channel']['caller']['number']
        
        print(f"[CALL] Incoming from {caller}, channel: {channel_id}")
        
        # Отвечаем на звонок
        channel = client.channels.get(channelId=channel_id)
        channel.answer()
        
        print(f"[CALL] Answered!")
        
        # Здесь можно добавить real-time обработку
        # Например, проигрывание звука или получение аудио
        
        # Пока просто держим линию 5 секунд
        import time
        time.sleep(5)
        
        # Вешаем трубку
        channel.hangup()
        print(f"[CALL] Hangup")
    
    # Регистрируем обработчик
    client.on_channel_event('StasisStart', on_start)
    
    # Запускаем
    print("[ARI] Listening for calls on app 'realtime_ai'...")
    client.run(apps='realtime_ai')
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

