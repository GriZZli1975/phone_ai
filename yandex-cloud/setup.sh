#!/bin/bash
# Скрипт настройки AI Call Center на Yandex Cloud VM
# Запустите на свежей Ubuntu 22.04 VM

set -e

echo "🚀 Настройка AI Call Center на Yandex Cloud"
echo "============================================"

# Обновление системы
echo "📦 Обновление системы..."
sudo apt-get update
sudo apt-get upgrade -y

# Установка Docker
echo "🐳 Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "Docker уже установлен"
fi

# Установка Docker Compose
echo "🐳 Установка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "Docker Compose уже установлен"
fi

# Установка Yandex Cloud CLI
echo "☁️ Установка Yandex Cloud CLI..."
if ! command -v yc &> /dev/null; then
    curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
    source ~/.bashrc
else
    echo "Yandex Cloud CLI уже установлен"
fi

# Создание директорий
echo "📁 Создание директорий..."
sudo mkdir -p /opt/ai-call-center
sudo mkdir -p /opt/ai-call-center/ssl
sudo mkdir -p /var/log/ai-call-center
sudo chown -R $USER:$USER /opt/ai-call-center

# Клонирование репозитория
echo "📥 Клонирование репозитория..."
cd /opt
if [ -d "/opt/ai-call-center/.git" ]; then
    cd ai-call-center
    git pull origin main
else
    git clone https://github.com/GriZZli1975/phone.git ai-call-center
    cd ai-call-center
fi

# Создание .env файла
echo "⚙️ Создание .env файла..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# PostgreSQL
POSTGRES_USER=callcenter
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=callcenter

# OpenAI
OPENAI_API_KEY=sk-YOUR-KEY-HERE

# ElevenLabs
ELEVENLABS_API_KEY=YOUR-KEY-HERE
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# SIP Provider (Новофон)
SIP_PROVIDER_HOST=sip.novofon.ru
SIP_USERNAME=YOUR-NOVOFON-USERNAME
SIP_PASSWORD=YOUR-NOVOFON-PASSWORD
SIP_PHONE_NUMBER=+7495XXXXXXX

# JWT Secret
JWT_SECRET=CHANGE_ME_RANDOM_STRING_32_CHARS

# Yandex Container Registry
YC_REGISTRY=cr.yandex/YOUR-REGISTRY-ID
EOF
    echo "⚠️  ВАЖНО: Отредактируйте файл /opt/ai-call-center/.env"
    echo "Добавьте ваши API ключи!"
fi

# Настройка firewall
echo "🔥 Настройка firewall..."
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8000/tcp # Backend API
sudo ufw allow 5060/udp # SIP (для FreeSWITCH когда добавите)
sudo ufw allow 16384:16394/udp # RTP (для FreeSWITCH)
sudo ufw --force enable

echo ""
echo "✅ Базовая настройка завершена!"
echo ""
echo "📝 СЛЕДУЮЩИЕ ШАГИ:"
echo "1. Отредактируйте /opt/ai-call-center/.env"
echo "2. Добавьте ваши API ключи (OpenAI, ElevenLabs)"
echo "3. Настройте Yandex Container Registry"
echo "4. Запустите: cd /opt/ai-call-center && docker-compose -f yandex-cloud/docker-compose.yc.yml up -d"
echo ""
echo "🌐 После запуска приложение будет доступно:"
echo "   http://$(curl -s ifconfig.me):8000"
echo ""

