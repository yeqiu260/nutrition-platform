"""调试 API - 用于测试 xAI Grok AI 功能"""

import logging
from fastapi import APIRouter
from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/test-grok")
async def test_grok():
    """测试 xAI Grok API 是否工作"""
    logger.info("=== Testing xAI Grok API ===")
    
    settings = get_settings()
    
    if not settings.grok_api_key:
        return {"status": "error", "message": "GROK_API_KEY not configured"}
        
    try:
        client = OpenAI(
            api_key=settings.grok_api_key,
            base_url="https://api.x.ai/v1"
        )
        
        response = client.chat.completions.create(
            model="grok-4-1-fast-reasoning",
            messages=[
                {"role": "user", "content": "Hello, are you ready? Please reply with 'Yes, I am Grok!'"}
            ],
            max_tokens=50
        )
        
        return {
            "status": "success", 
            "response": response.choices[0].message.content,
            "model": "grok-4-latest"
        }
    except Exception as e:
        logger.error(f"Grok test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

