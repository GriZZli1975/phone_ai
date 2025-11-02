"""
API эндпоинты для админ панели
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db, Call, Operator, RoutingRule
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import List

router = APIRouter()


class RoutingRuleCreate(BaseModel):
    name: str
    keywords: List[str]
    route_to: str
    priority: int = 0


@router.get("/stats")
async def get_stats(
    current_user: Operator = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить общую статистику"""
    
    # Всего звонков
    total_calls = await db.execute(select(func.count(Call.id)))
    total_calls_count = total_calls.scalar()
    
    # AI обработано
    ai_handled = await db.execute(
        select(func.count(Call.id)).where(Call.ai_handled == True)
    )
    ai_handled_count = ai_handled.scalar()
    
    # Активные звонки
    active_calls = await db.execute(
        select(func.count(Call.id)).where(Call.status == "active")
    )
    active_calls_count = active_calls.scalar()
    
    # Средняя длительность
    avg_duration = await db.execute(
        select(func.avg(Call.duration)).where(Call.duration > 0)
    )
    avg_duration_value = avg_duration.scalar() or 0
    
    return {
        "total_calls": total_calls_count,
        "ai_handled": ai_handled_count,
        "ai_handled_percent": (ai_handled_count / total_calls_count * 100) if total_calls_count > 0 else 0,
        "active_calls": active_calls_count,
        "avg_duration": int(avg_duration_value)
    }


@router.get("/operators")
async def get_operators(
    current_user: Operator = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список операторов"""
    result = await db.execute(select(Operator))
    operators = result.scalars().all()
    
    return {
        "operators": [
            {
                "id": op.id,
                "name": op.name,
                "email": op.email,
                "department": op.department,
                "sip_extension": op.sip_extension,
                "is_available": op.is_available,
                "current_call_uuid": op.current_call_uuid
            }
            for op in operators
        ]
    }


@router.get("/routing-rules")
async def get_routing_rules(
    current_user: Operator = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить правила маршрутизации"""
    result = await db.execute(
        select(RoutingRule).where(RoutingRule.is_active == True)
    )
    rules = result.scalars().all()
    
    return {
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "keywords": rule.keywords,
                "route_to": rule.route_to,
                "priority": rule.priority
            }
            for rule in rules
        ]
    }


@router.post("/routing-rules")
async def create_routing_rule(
    rule: RoutingRuleCreate,
    current_user: Operator = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать правило маршрутизации"""
    new_rule = RoutingRule(
        name=rule.name,
        keywords=rule.keywords,
        intent=rule.route_to,
        route_to=rule.route_to,
        priority=rule.priority
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    return {"id": new_rule.id, "status": "created"}


@router.delete("/routing-rules/{rule_id}")
async def delete_routing_rule(
    rule_id: int,
    current_user: Operator = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить правило маршрутизации"""
    result = await db.execute(
        select(RoutingRule).where(RoutingRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
        
    await db.delete(rule)
    await db.commit()
    
    return {"status": "deleted"}


@router.patch("/operators/{operator_id}/availability")
async def toggle_operator_availability(
    operator_id: int,
    is_available: bool,
    current_user: Operator = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Изменить доступность оператора"""
    result = await db.execute(
        select(Operator).where(Operator.id == operator_id)
    )
    operator = result.scalar_one_or_none()
    
    if not operator:
        raise HTTPException(status_code=404, detail="Оператор не найден")
        
    operator.is_available = is_available
    await db.commit()
    
    return {"status": "updated", "is_available": is_available}

