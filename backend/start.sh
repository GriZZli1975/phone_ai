#!/bin/bash
# Скрипт запуска AI сервера в зависимости от режима

# Загружаем .env
if [ -f "/opt/ai-call-center/.env" ]; then
    export $(cat /opt/ai-call-center/.env | grep -v '^#' | xargs)
fi

# Запускаем uvicorn в фоне
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Проверяем режим AI
AI_MODE=${AI_MODE:-fastagi}

echo "[START] AI Mode: $AI_MODE"

if [ "$AI_MODE" = "realtime" ]; then
    echo "[START] Starting AudioSocket server for real-time ElevenLabs Conversational AI..."
    python3 audiosocket_server.py
else
    echo "[START] Starting FastAGI server (default mode)..."
    python3 agi_handler.py
fi

