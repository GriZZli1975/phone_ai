# 📤 Загрузка кода в новый репозиторий

## Команды для заливки в GitHub

Выполните в терминале (в папке с проектом):

```bash
# 1. Инициализация Git (если ещё не сделано)
git init

# 2. Добавление удалённого репозитория
git remote add origin https://github.com/GriZZli1975/phone_ai.git

# 3. Добавление всех файлов
git add .

# 4. Создание коммита
git commit -m "🚀 Initial commit: Asterisk + OpenAI/ElevenLabs AI Call Center

- Asterisk 20 для SIP/RTP телефонии
- Python FastAGI для real-time обработки звонков
- OpenAI Whisper (STT) + GPT-4 (AI logic)
- ElevenLabs Text-to-Speech (TTS)
- GitHub Actions автодеплой на DigitalOcean
- Docker Compose инфраструктура
- PostgreSQL для хранения звонков
- Nginx frontend с мониторингом

Features:
✅ Real-time распознавание речи
✅ Автоматическая маршрутизация по отделам
✅ Интеграция с SIP провайдерами (Mango Office, Zadarma)
✅ Запись и хранение звонков
✅ Web dashboard для мониторинга"

# 5. Переименование ветки в main (если нужно)
git branch -M main

# 6. Загрузка в GitHub
git push -u origin main
```

---

## Если возникнут ошибки:

### Ошибка: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/GriZZli1975/phone_ai.git
git push -u origin main
```

### Ошибка: "failed to push some refs"
```bash
# Если репозиторий не пустой, сделайте force push
git push -u origin main --force
```

### Ошибка: "Please tell me who you are"
```bash
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"
```

---

## После загрузки:

1. Проверьте: https://github.com/GriZZli1975/phone_ai
2. Настройте GitHub Secrets (см. DEPLOY.md)
3. Сделайте первый деплой на DigitalOcean

✅ Готово!

