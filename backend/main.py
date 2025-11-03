"""
FastAPI backend для AI Call Center
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="AI Call Center API")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

