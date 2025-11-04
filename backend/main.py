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


@app.post("/api/transfer/{caller_number}/{department}")
async def transfer_call(caller_number: str, department: str):
    """Перевод звонка через Mango API"""
    call_id = active_calls.get(caller_number)
    
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
        api_key = os.getenv('MANGO_API_KEY')
        api_salt = os.getenv('MANGO_API_SALT')
        
        params = {
            "call_id": call_id,
            "to_number": to_number,
            "command_id": f"transfer_{call_id}"
        }
        
        # Подпись
        sign_str = json.dumps(params, separators=(',', ':')) + api_key + api_salt
        sign = hashlib.sha256(sign_str.encode()).hexdigest()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://app.mango-office.ru/vpbx/commands/transfer",
                json=params,
                headers={"sign": sign}
            )
        
        print(f"[MANGO] Transfer response: {response.status_code} {response.text}", flush=True)
        return {"status": "ok", "response": response.json()}
        
    except Exception as e:
        print(f"[MANGO] Transfer error: {e}", flush=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

