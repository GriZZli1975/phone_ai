# 🚀 Деплой на DigitalOcean с GitHub Actions

## Шаг 1: Настройка GitHub Secrets

1. Откройте ваш репозиторий на GitHub: https://github.com/GriZZli1975/phone_ai

2. Перейдите в **Settings** → **Secrets and variables** → **Actions**

3. Нажмите **"New repository secret"** и добавьте:

### Secret 1: DO_HOST
```
Name: DO_HOST
Value: 64.226.125.167
```

### Secret 2: DO_PASSWORD
```
Name: DO_PASSWORD
Value: ziG-hrT-VB4-e9J
```

4. Нажмите **"Add secret"** для каждого

---

## Шаг 2: Первичный деплой на сервер

### Подключитесь к серверу:

```bash
ssh root@64.226.125.167
# Введите пароль: ziG-hrT-VB4-e9J
```

### Выполните команды:

```bash
# 1. Установка Docker
curl -fsSL https://get.docker.com | sh
apt install docker-compose -y

# 2. Настройка firewall
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5060/udp
ufw allow 5060/tcp
ufw allow 10000:20000/udp

# 3. Клонирование репозитория
cd /opt
git clone https://github.com/GriZZli1975/phone_ai.git ai-call-center
cd ai-call-center

# 4. Создание .env файла
cp env.example .env
nano .env
```

### Заполните .env:

```env
# OpenAI
OPENAI_API_KEY=sk-ваш-ключ

# ElevenLabs
ELEVENLABS_API_KEY=ваш-ключ
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# SIP Provider (например, Mango Office)
SIP_PROVIDER_HOST=sip.mango-office.ru
SIP_USERNAME=ваш_логин
SIP_PASSWORD=ваш_пароль
SIP_TRUNK_NUMBER=+78126434217

# Database
POSTGRES_PASSWORD=securepass123

# JWT
JWT_SECRET=change-this-to-random-string
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### Запустите систему:

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Шаг 3: Проверка автодеплоя

### Сделайте тестовый коммит:

```bash
# На вашем локальном компьютере
cd /путь/к/репозиторию
echo "Test" >> test.txt
git add test.txt
git commit -m "Test auto-deploy"
git push origin main
```

### Проверьте GitHub Actions:

1. Откройте: https://github.com/GriZZli1975/phone_ai/actions
2. Вы должны увидеть запущенный workflow "Deploy to DigitalOcean"
3. Дождитесь зелёной галочки ✅

### Проверьте на сервере:

```bash
ssh root@64.226.125.167
cd /opt/ai-call-center
git log -1  # Должен показать ваш последний коммит
docker-compose ps  # Все контейнеры должны быть Up
```

---

## 🎉 Готово!

Теперь при каждом `git push` в ветку `main`:
1. GitHub Actions автоматически подключится к серверу
2. Выполнит `git pull`
3. Перезапустит Docker контейнеры
4. Покажет логи

---

## 📊 Мониторинг

### Просмотр логов:

```bash
# Все сервисы
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только Asterisk
docker-compose logs -f asterisk
```

### Проверка статуса:

```bash
docker-compose ps
docker exec -it asterisk asterisk -rx "pjsip show endpoints"
docker exec -it asterisk asterisk -rx "core show channels"
```

### Web интерфейс:

Откройте в браузере: **http://64.226.125.167**

---

## 🔧 Troubleshooting

### GitHub Actions не запускается:

- Проверьте что Secrets добавлены правильно
- Проверьте что branch называется `main` (не `master`)

### Не подключается к серверу:

```bash
# Проверьте SSH подключение вручную:
ssh root@64.226.125.167

# Если не работает - проверьте IP и пароль
```

### Docker контейнеры не стартуют:

```bash
# Проверьте логи:
docker-compose logs

# Проверьте что .env файл заполнен:
cat .env | grep API_KEY
```

