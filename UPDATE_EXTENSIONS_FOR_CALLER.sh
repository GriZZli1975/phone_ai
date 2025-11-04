#!/bin/bash
# Патч extensions.conf для передачи caller_number в AudioSocket

cat > /opt/ai-call-center/asterisk/conf/extensions.conf << 'EOF'
[general]
static=yes
writeprotect=no

[from-trunk]
exten => _X.,1,NoOp(=== Incoming call from ${CALLERID(num)} ===)
 same => n,Answer()
 same => n,Set(CALL_ID=${EPOCH})
 same => n,Goto(from-trunk-realtime,${EXTEN},1)

[from-trunk-realtime]
exten => _X.,1,NoOp(=== Real-time AudioSocket Mode ===)
 ; Передаём номер звонящего как UUID
 same => n,AudioSocket(${CALLERID(num)},172.18.0.1:9092)
 same => n,Hangup()

[internal]
exten => _X.,1,NoOp(=== Outgoing call to ${EXTEN} ===)
 same => n,Dial(PJSIP/${EXTEN}@trunk,60)
 same => n,Hangup()
EOF

echo "✅ extensions.conf updated - caller_number will be sent as UUID"

