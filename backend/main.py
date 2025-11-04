"""
FastAPI backend для AI Call Center
"""
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import hashlib
import json
import httpx

app = FastAPI(title="AI Call Center API")

# Хранилище активных звонков: {caller_number: call_id}
active_calls = {}
# Маппинг conversation_id → caller_number
conversation_to_caller = {}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "running",
        "service": "AI Call Center",
        "version": "1.0.0"
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "openai": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
        "elevenlabs": "configured" if os.getenv('ELEVENLABS_API_KEY') else "missing"
    }


@app.get("/api/calls")
async def get_calls():
    """Get recent calls (placeholder)"""
    return {
        "calls": [],
        "total": 0
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для real-time обновлений"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except:
        pass


@app.post("/api/mango/webhook")
async def mango_webhook(request: Request):
    """Webhook от Mango Office для отслеживания звонков"""
    try:
        data = await request.json()
        event_type = data.get('event')
        
        if event_type == 'call.connected':
            call_id = data.get('call_id')
            from_number = data.get('from', {}).get('number', '')
            print(f"[MANGO] Call connected: {call_id} from {from_number}", flush=True)
            # Сохраняем call_id для возможного перевода
            if from_number:
                active_calls[from_number] = call_id
        
        elif event_type == 'call.disconnected':
            from_number = data.get('from', {}).get('number', '')
            if from_number in active_calls:
                del active_calls[from_number]
        
        return {"status": "ok"}
    except Exception as e:
        print(f"[MANGO] Webhook error: {e}", flush=True)
        return {"status": "error", "message": str(e)}


@app.post("/api/transfer/{key}/{department}")
async def transfer_call(key: str, department: str):
    """Перевод звонка через Mango API"""
    # Пробуем найти call_id:
    # 1. По прямому ключу (caller_number)
    call_id = active_calls.get(key)
    
    # 2. Если не нашли - пробуем через conversation_to_caller
    if not call_id and key in conversation_to_caller:
        caller_number = conversation_to_caller[key]
        call_id = active_calls.get(caller_number)
    
    # 3. Если только один активный звонок - берём его (fallback)
    if not call_id and len(active_calls) == 1:
        call_id = list(active_calls.values())[0]
        print(f"[MANGO] Using single active call: {call_id}", flush=True)
    
    if not call_id:
        return {"status": "error", "message": "Call ID not found"}
    
    # Маппинг отделов на добавочные Mango
    dept_map = {
        'sales': '101',      # TODO: заменить на реальные
        'support': '102',
        'billing': '103',
        'quality': '104'
    }
    
    to_number = dept_map.get(department, '101')
    
    # Вызов Mango API
    try:
        api_key = os.getenv('MANGO_API_KEY', '')
        api_salt = os.getenv('MANGO_API_SALT', '')
        
        if not api_key or not api_salt:
            print(f"[MANGO] ERROR: MANGO_API_KEY or MANGO_API_SALT not configured", flush=True)
            return {"status": "error", "message": "Mango API keys not configured"}
        
        params = {
            "call_id": call_id,
            "to_number": to_number,
            "command_id": f"transfer_{call_id}"
        }
        
        # Подпись: JSON + key + salt по документации Mango
        json_str = json.dumps(params, ensure_ascii=False, separators=(',', ':'))
        sign_str = json_str + api_key + api_salt
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        
        print(f"[MANGO] Calling transfer: call_id={call_id}, to={to_number}", flush=True)
        print(f"[MANGO] DEBUG: json={json_str[:100]}", flush=True)
        
        # Формат запроса: form-data с полем json
        payload = {
            "vpbx_api_key": api_key,
            "sign": sign,
            "json": json_str
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://app.mango-office.ru/vpbx/commands/transfer",
                data=payload,  # form-data вместо json
                timeout=10.0
            )
        
        print(f"[MANGO] Transfer response: {response.status_code} {response.text}", flush=True)
        return {"status": "ok", "response": response.json()}
        
    except Exception as e:
        print(f"[MANGO] Transfer error: {e}", flush=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

