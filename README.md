# 🤖 AI Call Center

Real-time телефония с AI для автоматической маршрутизации звонков через OpenAI и ElevenLabs.

## 🏗️ Архитектура

- **Asterisk 20** — телефония (SIP/RTP)
- **Python FastAPI** — backend API
- **FastAGI** — real-time обработка звонков
- **OpenAI Whisper** — STT (Speech-to-Text)
- **OpenAI GPT-4** — определение отдела
- **ElevenLabs** — TTS (Text-to-Speech)
- **PostgreSQL** — база данных
- **Nginx** — frontend + reverse proxy
- **Docker** — контейнеризация

## 🚀 Быстрый старт

### 1. Подключитесь к серверу

```bash
ssh root@64.226.125.167
# Пароль: ziG-hrT-VB4-e9J
```

### 2. Установите Docker

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose -y
```

### 3. Клонируйте репозиторий

```bash
cd /opt
git clone https://github.com/GriZZli1975/phone_ai.git ai-call-center
cd ai-call-center
```

### 4. Настройте переменные окружения

```bash
cp env.example .env
nano .env
```

Заполните:
```env
OPENAI_API_KEY=sk-your-key-here
ELEVENLABS_API_KEY=your-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# SIP Provider
SIP_PROVIDER_HOST=sip.your-provider.com
SIP_USERNAME=your_username
SIP_PASSWORD=your_password
SIP_TRUNK_NUMBER=+78126434217

POSTGRES_PASSWORD=securepass123
JWT_SECRET=change-this-secret-key
```

### 5. Настройте firewall

```bash
# Открываем порты
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 5060/udp # SIP
ufw allow 5060/tcp # SIP over TCP
ufw allow 10000:20000/udp  # RTP
ufw enable
```

### 6. Запустите контейнеры

```bash
docker-compose up -d
```

### 7. Проверьте статус

```bash
docker-compose ps
docker-compose logs -f backend
```

Откройте в браузере: **http://64.226.125.167**

## 🔄 Автоматический деплой из GitHub

### Настройка GitHub Secrets

1. Откройте репозиторий: https://github.com/GriZZli1975/phone_ai
2. **Settings** → **Secrets and variables** → **Actions**
3. Добавьте secrets:
   - `DO_HOST` = `64.226.125.167`
   - `DO_PASSWORD` = `ziG-hrT-VB4-e9J`

Теперь при каждом `git push` проект автоматически обновится на сервере!

## 📞 Настройка SIP trunk

### Настройка Mango Office (IP-based trunk, без регистрации)

**Важно:** Mango Office использует IP-based SIP trunk без авторизации!

1. В личном кабинете Mango Office (https://app.mango-office.ru/):
   - **Настройки** → **Настройки SIP** → **SIP Trunk**
   - Нажмите **"Добавить SIP TRUNK"** → выберите **"Внешний"**
   - **IP-адрес**: `64.226.125.167`
   - **Порт**: `5060`
   - Сохраните

2. Настройте маршрутизацию входящих звонков:
   - **Схема распределения звонков**
   - Выберите ваш номер → **Направить на SIP Trunk**

3. В `.env` **НЕ НУЖНО** заполнять SIP данные (они не используются)

Документация: https://cdn.mango-office.ru/project-im/iblock/b64/MO_SIP_Trunk.pdf

### Пример для Zadarma (Novofon)

В `.env`:
```env
SIP_PROVIDER_HOST=sip.zadarma.com
SIP_USERNAME=ваш_номер
SIP_PASSWORD=ваш_пароль
```

## 🧪 Тестирование

### Проверка Asterisk

```bash
docker exec -it asterisk asterisk -rvvv
# В консоли Asterisk:
pjsip show endpoints
pjsip show registrations
core show channels
```

### Проверка FastAGI

```bash
docker-compose logs -f backend | grep AGI
```

### Тестовый звонок

Позвоните на ваш SIP номер. В логах должно появиться:
```
[AGI] New connection from...
[STT] Processing: /recordings/call_xxx.wav
[AI] Processing: текст клиента
[AI] Response: support
[TTS] Generating speech...
```

## 📝 Разработка

### Локальные изменения

```bash
# Измените код локально
git add .
git commit -m "Update feature"
git push origin main

# GitHub Actions автоматически задеплоит на сервер!
```

### Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только Asterisk
docker exec -it asterisk tail -f /var/log/asterisk/full
```

## 🛠️ Troubleshooting

### Asterisk не регистрируется

```bash
docker exec -it asterisk asterisk -rx "pjsip show registrations"
docker-compose logs asterisk | grep -i error
```

Проверьте:
- Правильность `SIP_USERNAME`, `SIP_PASSWORD` в `.env`
- IP сервера в whitelist у провайдера
- Открыты ли порты 5060 UDP/TCP

### FastAGI не отвечает

```bash
docker-compose logs backend | grep AGI
netstat -tlnp | grep 4573
```

Проверьте:
- Запущен ли `agi_handler.py`: `docker-compose exec backend ps aux | grep agi`
- Доступен ли порт 4573: `telnet localhost 4573`

### OpenAI/ElevenLabs ошибки

```bash
docker-compose exec backend python3 -c "import os; print(os.getenv('OPENAI_API_KEY')[:20])"
```

Проверьте наличие ключей в `.env` и перезапустите:
```bash
docker-compose restart backend
```

## 🎯 Roadmap

- [x] Базовая интеграция Asterisk
- [x] FastAGI для real-time обработки
- [x] OpenAI Whisper STT
- [x] OpenAI GPT-4 для определения отдела
- [x] ElevenLabs TTS
- [x] GitHub Actions автодеплой
- [ ] WebSocket для real-time мониторинга
- [ ] Dashboard для операторов
- [ ] Запись и хранение звонков в БД
- [ ] Аналитика и отчёты
- [ ] Интеграция с CRM

## 📄 Лицензия

MIT

## 🤝 Поддержка

Вопросы? Создайте Issue: https://github.com/GriZZli1975/phone_ai/issues

