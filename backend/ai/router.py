"""
AI Router - интеллектуальная маршрутизация звонков
Анализирует запрос клиента и направляет на нужного оператора/отдел
"""

import logging
from typing import Optional, Dict
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class CallRouter:
    """Маршрутизатор звонков на основе AI"""
    
    # Доступные направления
    ROUTES = {
        "sales": {
            "name": "Отдел продаж",
            "extension": "101",
            "keywords": ["купить", "заказ", "продажа", "стоимость", "цена"]
        },
        "support": {
            "name": "Техподдержка",
            "extension": "102",
            "keywords": ["проблема", "не работает", "ошибка", "поломка", "помощь"]
        },
        "billing": {
            "name": "Бухгалтерия",
            "extension": "103",
            "keywords": ["оплата", "счет", "платеж", "возврат", "деньги"]
        },
        "ai_consultant": {
            "name": "AI Консультант",
            "extension": "ai",
            "keywords": []  # default fallback
        }
    }
    
    async def route_call(self, client_text: str, context: Optional[Dict] = None) -> Dict:
        """
        Определить куда направить звонок
        
        Returns:
            {
                "route_to": "sales",
                "confidence": 0.95,
                "reason": "Клиент спрашивает о покупке продукта"
            }
        """
        
        if not settings.AI_ROUTING_ENABLED:
            return {
                "route_to": "ai_consultant",
                "confidence": 1.0,
                "reason": "AI routing disabled"
            }
            
        try:
            # Используем GPT для анализа намерения
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""Ты - система маршрутизации звонков колл-центра.
Твоя задача - определить куда направить клиента на основе его запроса.

Доступные отделы:
- sales (продажи): вопросы о покупке, заказе, стоимости продуктов
- support (техподдержка): проблемы, ошибки, неисправности
- billing (бухгалтерия): вопросы об оплате, счетах, возвратах
- ai_consultant (AI консультант): простые вопросы, которые AI может решить сам

Ответь СТРОГО в формате JSON:
{{
    "route_to": "название_отдела",
    "confidence": 0.0-1.0,
    "reason": "краткое объяснение"
}}"""
                    },
                    {
                        "role": "user",
                        "content": f"Запрос клиента: {client_text}"
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Проверяем confidence threshold
            if result["confidence"] < settings.AI_ROUTING_CONFIDENCE_THRESHOLD:
                logger.warning(f"Низкая уверенность маршрутизации: {result['confidence']}")
                result["route_to"] = "ai_consultant"  # fallback
                
            logger.info(f"📍 Маршрут определен: {result['route_to']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка маршрутизации: {e}", exc_info=True)
            return {
                "route_to": "ai_consultant",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}"
            }
            
    async def get_route_info(self, route_to: str) -> Dict:
        """Получить информацию о маршруте"""
        return self.ROUTES.get(route_to, self.ROUTES["ai_consultant"])
        
    async def analyze_intent(self, text: str) -> str:
        """Быстрый анализ намерения (без полной маршрутизации)"""
        text_lower = text.lower()
        
        for route_name, route_info in self.ROUTES.items():
            for keyword in route_info["keywords"]:
                if keyword in text_lower:
                    return route_name
                    
        return "ai_consultant"


# Глобальный экземпляр
call_router = CallRouter()

