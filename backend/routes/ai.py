"""
API эндпоинты для AI функций
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai.router import call_router
from ai.consultant import ai_consultant
from ai.supervisor import supervisor_ai

router = APIRouter()


class RouteRequest(BaseModel):
    """Запрос на маршрутизацию"""
    text: str
    context: dict = None


class ConsultantRequest(BaseModel):
    """Запрос к AI консультанту"""
    call_id: str
    message: str


class SupervisorRequest(BaseModel):
    """Запрос суфлера"""
    call_id: str
    operator_id: str


@router.post("/route")
async def route_call(request: RouteRequest):
    """
    Определить маршрут звонка
    
    Пример:
    ```
    POST /api/ai/route
    {
        "text": "Хочу купить ваш продукт",
        "context": {}
    }
    ```
    """
    result = await call_router.route_call(
        client_text=request.text,
        context=request.context
    )
    return result


@router.post("/consultant/message")
async def consultant_message(request: ConsultantRequest):
    """
    Отправить сообщение AI консультанту
    
    Пример:
    ```
    POST /api/ai/consultant/message
    {
        "call_id": "uuid-123",
        "message": "Какие у вас часы работы?"
    }
    ```
    """
    response = await ai_consultant.process_message(
        call_id=request.call_id,
        client_message=request.message
    )
    return response


@router.post("/consultant/start")
async def consultant_start(call_id: str):
    """Начать разговор с AI консультантом"""
    greeting = await ai_consultant.start_conversation(call_id)
    return {"greeting": greeting}


@router.post("/consultant/end")
async def consultant_end(call_id: str):
    """Завершить разговор с AI консультантом"""
    await ai_consultant.end_conversation(call_id)
    return {"status": "ended"}


@router.post("/consultant/audio")
async def generate_audio(text: str):
    """Сгенерировать аудио ответ"""
    audio_url = await ai_consultant.generate_audio_response(text)
    if not audio_url:
        raise HTTPException(status_code=500, detail="Ошибка генерации аудио")
    return {"audio_url": audio_url}


@router.post("/supervisor/start")
async def supervisor_start(request: SupervisorRequest):
    """Запустить суфлера для звонка"""
    await supervisor_ai.start_supervision(
        call_id=request.call_id,
        operator_id=request.operator_id
    )
    return {"status": "started"}


@router.post("/supervisor/stop")
async def supervisor_stop(call_id: str):
    """Остановить суфлера"""
    await supervisor_ai.stop_supervision(call_id)
    return {"status": "stopped"}


@router.post("/supervisor/transcript")
async def supervisor_add_transcript(
    call_id: str,
    speaker: str,
    text: str
):
    """Добавить транскрипцию реплики"""
    await supervisor_ai.add_transcript(call_id, speaker, text)
    return {"status": "added"}


@router.get("/health")
async def ai_health():
    """Проверка здоровья AI сервисов"""
    return {
        "status": "healthy",
        "services": {
            "router": "ready",
            "consultant": "ready",
            "supervisor": "ready"
        }
    }

