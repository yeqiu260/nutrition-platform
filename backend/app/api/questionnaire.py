"""问卷 API 路由"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.questionnaire import (
    QuestionnaireService,
    Questionnaire,
    QuestionAnswerInput,
    ValidationResult,
    RecommendationSessionResponse,
)

router = APIRouter(prefix="/api/questionnaire", tags=["questionnaire"])


async def get_questionnaire_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionnaireService:
    """获取问卷服务依赖"""
    return QuestionnaireService(db)


@router.get("/", response_model=Questionnaire)
async def get_questionnaire(
    locale: str = "zh-TW",
    questionnaire_service: Annotated[QuestionnaireService, Depends(get_questionnaire_service)] = None,
) -> Questionnaire:
    """
    获取问卷定义

    - **locale**: 语言代码（"zh-TW" 或 "en"）
    """
    try:
        return questionnaire_service.get_questionnaire(locale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate", response_model=ValidationResult)
async def validate_answers(
    answers: list[QuestionAnswerInput],
    questionnaire_service: Annotated[QuestionnaireService, Depends(get_questionnaire_service)] = None,
) -> ValidationResult:
    """
    验证问卷答案

    - **answers**: 问卷答案列表
    """
    try:
        return questionnaire_service.validate_answers(answers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit", response_model=RecommendationSessionResponse)
async def submit_answers(
    user_id: str,
    answers: list[QuestionAnswerInput],
    questionnaire_service: Annotated[QuestionnaireService, Depends(get_questionnaire_service)] = None,
) -> RecommendationSessionResponse:
    """
    提交问卷答案

    - **user_id**: 用户 ID
    - **answers**: 问卷答案列表
    """
    try:
        user_uuid = UUID(user_id)
        return await questionnaire_service.submit_answers(user_uuid, answers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
