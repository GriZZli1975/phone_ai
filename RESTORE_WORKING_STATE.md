# 🔄 ВОССТАНОВЛЕНИЕ РАБОЧЕЙ ВЕРСИИ AI CALL CENTER

## ✅ Рабочая конфигурация (проверено 04.11.2025)

**Статус**: ВСЁ РАБОТАЕТ - ElevenLabs слышит пользователя, пользователь слышит бота

---

## 🚀 Быстрое восстановление

```bash
cd /opt/ai-call-center
git reset --hard be8bfff
docker-compose down
docker-compose build backend
docker-compose up -d
sleep 10

# Исправить extensions.conf
sed -i 's/from-trunk-fastagi/from-trunk-realtime/' asterisk/conf/extensions.conf

# Добавить правильный контекст from-trunk-realtime
cat >> asterisk/conf/extensions.conf << 'EOF'

; === Real-time режим (ElevenLabs Conversational AI) ===
[from-trunk-realtime]
exten => _X.,1,NoOp(=== Real-time AudioSocket Mode ===)
 same => n,AudioSocket(40325858-5f87-4274-80d5-6626cf17434c,172.18.0.1:9092)
 same => n,Hangup()
EOF

# Перезагрузить dialplan
docker-compose exec asterisk asterisk -rx "dialplan reload"

# Проверить логи
docker-compose logs -f backend | grep -E 'AUDIOSOCKET|ELEVEN'
```

---

## 🔒 Firewall (защита от утечки кредитов)

```bash
# Удалить глобальный DENY (если есть)
ufw status numbered | grep "9092/tcp.*DENY"
# Если видите правило - удалите: ufw delete [номер]

# Разрешить только Docker-сеть
ufw allow from 172.18.0.0/16 to any port 9092
ufw allow from 127.0.0.1 to any port 9092

# Проверить
ufw status | grep 9092
```

Должно быть:
```
9092    ALLOW    127.0.0.1
9092    ALLOW    172.18.0.0/16
```

**БЕЗ** `9092/tcp DENY Anywhere` перед ними!

---

## ⚙️ Ключевые параметры

### docker-compose.yml
```yaml
backend:
  ports:
    - "8000:8000"
    - "9092:9092"  # НЕ "127.0.0.1:9092:9092"!
```

### asterisk/conf/extensions.conf
```
[from-trunk]
 same => n,Goto(from-trunk-realtime,${EXTEN},1)  # ← realtime!

[from-trunk-realtime]
exten => _X.,1,NoOp(=== Real-time AudioSocket Mode ===)
 same => n,AudioSocket(40325858-5f87-4274-80d5-6626cf17434c,172.18.0.1:9092)
 same => n,Hangup()
```

### backend/audiosocket_server.py
- Задержка: `await asyncio.sleep(0.01)` или без задержки
- НЕ использовать `asyncio.wait(..., FIRST_COMPLETED)` с отменой задач

### ElevenLabs агент
- User input: **μ-law 8000 Hz**
- TTS output: **μ-law 8000 Hz**

---

## 📞 Проверка

Позвоните на **+7 (812) 643-42-17** с мобильного (НЕ от 1001!)

Должны появиться логи:
```
[AUDIOSOCKET] New connection from ('172.18.0.1', ...)
[ELEVEN] 👤 USER said: ...
[ELEVEN] Agent says: ...
[AUDIOSOCKET] ⬅️ Sent frame #1-100...
```

---

**Git коммит**: be8bfff  
**Тег**: v1.0-stable  
**Сервер**: root@64.226.125.167  
**Проект**: /opt/ai-call-center

