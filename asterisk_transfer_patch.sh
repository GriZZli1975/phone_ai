#!/bin/bash
# Патч для добавления логики перевода в extensions.conf

cat > /tmp/realtime_with_transfer.txt << 'EOF'

; === Real-time режим с поддержкой переводов ===
[from-trunk-realtime]
exten => _X.,1,NoOp(=== Real-time AudioSocket Mode ===)
 same => n,AudioSocket(40325858-5f87-4274-80d5-6626cf17434c,172.18.0.1:9092)
 ; После AudioSocket проверяем файл перевода
 same => n,Set(TRANSFER_FILE=/tmp/transfer_${CALL_ID})
 same => n,GotoIf($[${STAT(e,${TRANSFER_FILE})}]?do_transfer:end)
 same => n(do_transfer),Set(TRANSFER_URI=${FILE(${TRANSFER_FILE},0,100)})
 same => n,NoOp(=== Transferring to ${TRANSFER_URI} ===)
 same => n,System(rm -f ${TRANSFER_FILE})
 same => n,Dial(${TRANSFER_URI},30)
 same => n(end),Hangup()
EOF

# Удаляем старый контекст from-trunk-realtime
sed -i '/\[from-trunk-realtime\]/,/^\[/{/^\[from-trunk-realtime\]/!{/^\[/!d}}' /opt/ai-call-center/asterisk/conf/extensions.conf

# Удаляем комментарий "Real-time режим"
sed -i '/; === Real-time режим/d' /opt/ai-call-center/asterisk/conf/extensions.conf

# Добавляем новый контекст
cat /tmp/realtime_with_transfer.txt >> /opt/ai-call-center/asterisk/conf/extensions.conf

echo "✅ extensions.conf updated with transfer support"

