FROM debian:bullseye-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Добавление FreeSWITCH репозитория
RUN wget -O - https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc | apt-key add - && \
    echo "deb https://files.freeswitch.org/repo/deb/debian-release/ bullseye main" > /etc/apt/sources.list.d/freeswitch.list

# Установка FreeSWITCH
RUN apt-get update && apt-get install -y \
    freeswitch-meta-all \
    freeswitch-mod-commands \
    freeswitch-mod-conference \
    freeswitch-mod-db \
    freeswitch-mod-dptools \
    freeswitch-mod-event-socket \
    freeswitch-mod-sofia \
    freeswitch-mod-dialplan-xml \
    freeswitch-mod-shout \
    && rm -rf /var/lib/apt/lists/*

# Создание директорий
RUN mkdir -p /var/lib/freeswitch/recordings \
    /var/log/freeswitch \
    /etc/freeswitch

# Expose порты
EXPOSE 5060/udp 5060/tcp 5080/tcp 8021 16384-16394/udp

# Точка входа
CMD ["/usr/bin/freeswitch", "-nonat", "-nc"]

