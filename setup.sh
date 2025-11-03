#!/bin/bash
set -e

echo "========================================="
echo "  AI Call Center - Quick Setup Script"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

echo -e "${GREEN}[1/7] Updating system...${NC}"
apt update && apt upgrade -y

echo -e "${GREEN}[2/7] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "Docker already installed"
fi

echo -e "${GREEN}[3/7] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    apt install docker-compose -y
else
    echo "Docker Compose already installed"
fi

echo -e "${GREEN}[4/7] Configuring firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5060/udp
ufw allow 5060/tcp
ufw allow 10000:20000/udp
ufw reload

echo -e "${GREEN}[5/7] Creating directories...${NC}"
mkdir -p /opt/ai-call-center
mkdir -p /opt/ai-call-center/recordings
chmod 777 /opt/ai-call-center/recordings

echo -e "${GREEN}[6/7] Cloning repository...${NC}"
cd /opt
if [ -d "ai-call-center/.git" ]; then
    cd ai-call-center
    git pull origin main
else
    rm -rf ai-call-center
    git clone https://github.com/GriZZli1975/phone_ai.git ai-call-center
    cd ai-call-center
fi

echo -e "${GREEN}[7/7] Setting up environment...${NC}"
if [ ! -f ".env" ]; then
    cp env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your API keys:${NC}"
    echo "    nano .env"
    echo ""
    echo "Required:"
    echo "  - OPENAI_API_KEY"
    echo "  - ELEVENLABS_API_KEY"
    echo "  - SIP_PROVIDER_HOST"
    echo "  - SIP_USERNAME"
    echo "  - SIP_PASSWORD"
fi

echo ""
echo -e "${GREEN}========================================="
echo "  Setup Complete!"
echo "=========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit configuration: nano /opt/ai-call-center/.env"
echo "  2. Start services: cd /opt/ai-call-center && docker-compose up -d"
echo "  3. View logs: docker-compose logs -f"
echo "  4. Open in browser: http://$(curl -s ifconfig.me)"
echo ""

