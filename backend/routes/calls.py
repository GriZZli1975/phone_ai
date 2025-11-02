"""
API эндпоинты для работы со звонками
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from database import get_db, Call
from datetime import datetime

router = APIRouter()


@router.get("/")
async def get_calls(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Получить список звонков"""
    result = await db.execute(
        select(Call)
        .order_by(Call.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    calls = result.scalars().all()
    
    return {
        "calls": [
            {
                "id": call.id,
                "uuid": call.uuid,
                "caller_number": call.caller_number,
                "called_number": call.called_number,
                "direction": call.direction,
                "status": call.status,
                "duration": call.duration,
                "ai_handled": call.ai_handled,
                "ai_routed_to": call.ai_routed_to,
                "start_time": call.start_time.isoformat() if call.start_time else None,
                "end_time": call.end_time.isoformat() if call.end_time else None,
            }
            for call in calls
        ],
        "total": len(calls),
        "limit": limit,
        "offset": offset
    }


@router.get("/{call_id}")
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    """Получить детали звонка"""
    result = await db.execute(
        select(Call).where(Call.uuid == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")
        
    return {
        "id": call.id,
        "uuid": call.uuid,
        "caller_number": call.caller_number,
        "called_number": call.called_number,
        "direction": call.direction,
        "status": call.status,
        "duration": call.duration,
        "ai_handled": call.ai_handled,
        "ai_routed_to": call.ai_routed_to,
        "ai_confidence": call.ai_confidence,
        "recording_path": call.recording_path,
        "transcript": call.transcript,
        "metadata": call.metadata,
        "start_time": call.start_time.isoformat() if call.start_time else None,
        "answer_time": call.answer_time.isoformat() if call.answer_time else None,
        "end_time": call.end_time.isoformat() if call.end_time else None,
    }


@router.get("/{call_id}/transcript")
async def get_call_transcript(call_id: str, db: AsyncSession = Depends(get_db)):
    """Получить транскрипцию звонка"""
    result = await db.execute(
        select(Call).where(Call.uuid == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")
        
    return {
        "call_uuid": call.uuid,
        "transcript": call.transcript,
        "duration": call.duration
    }


@router.get("/{call_id}/recording")
async def get_call_recording(call_id: str, db: AsyncSession = Depends(get_db)):
    """Получить запись звонка"""
    result = await db.execute(
        select(Call).where(Call.uuid == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")
        
    if not call.recording_path:
        raise HTTPException(status_code=404, detail="Запись не найдена")
        
    return {
        "call_uuid": call.uuid,
        "recording_url": f"/recordings/{call.recording_path}"
    }


@router.get("/active/list")
async def get_active_calls(db: AsyncSession = Depends(get_db)):
    """Получить список активных звонков"""
    result = await db.execute(
        select(Call).where(Call.status == "active")
    )
    calls = result.scalars().all()
    
    return {
        "active_calls": [
            {
                "uuid": call.uuid,
                "caller_number": call.caller_number,
                "duration": (datetime.utcnow() - call.start_time).seconds if call.start_time else 0,
                "ai_routed_to": call.ai_routed_to
            }
            for call in calls
        ],
        "count": len(calls)
    }

