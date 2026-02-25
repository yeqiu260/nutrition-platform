"""问卷服务 - 问卷定义、获取、答案提交和验证"""

from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# from app.models.user import HealthProfile, QuestionAnswer, User
from app.models.user import User  # 只导入 User
from app.models.recommendation import RecommendationSession


class LocalizedString(BaseModel):
    """本地化字符串"""

    zh_tw: str
    en: str


class QuestionOption(BaseModel):
    """问题选项"""

    value: str
    label: LocalizedString


class Question(BaseModel):
    """问题定义"""

    id: str
    type: str  # "single" | "multi" | "text" | "number"
    required: bool
    label: LocalizedString
    options: Optional[List[QuestionOption]] = None
    validation: Optional[dict] = None


class Questionnaire(BaseModel):
    """问卷定义"""

    id: str
    version: str
    questions: List[Question]


class QuestionAnswerInput(BaseModel):
    """问卷答案输入"""

    question_id: str
    value: Union[str, List[str], int, float]


class ValidationError(BaseModel):
    """验证错误"""

    question_id: str
    error: str


class ValidationResult(BaseModel):
    """验证结果"""

    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)


class RecommendationSessionResponse(BaseModel):
    """推荐会话响应"""

    session_id: str
    created_at: datetime


class QuestionnaireService:
    """问卷服务"""

    def __init__(self, db: AsyncSession):
        """初始化问卷服务"""
        self.db = db

    def get_questionnaire(self, locale: str = "zh-TW") -> Questionnaire:
        """
        获取问卷定义

        Args:
            locale: 语言代码（"zh-TW" 或 "en"）

        Returns:
            Questionnaire: 问卷定义
        """
        # 问卷定义（硬编码，实际应从数据库读取）
        questions = [
            Question(
                id="q1",
                type="multi",
                required=True,
                label=LocalizedString(
                    zh_tw="您的健康目标是什么？（可多选）",
                    en="What are your health goals? (Multiple selection)"
                ),
                options=[
                    QuestionOption(
                        value="weight_loss",
                        label=LocalizedString(zh_tw="减重", en="Weight Loss")
                    ),
                    QuestionOption(
                        value="muscle_gain",
                        label=LocalizedString(zh_tw="增肌", en="Muscle Gain")
                    ),
                    QuestionOption(
                        value="energy",
                        label=LocalizedString(zh_tw="增加能量", en="Increase Energy")
                    ),
                    QuestionOption(
                        value="immunity",
                        label=LocalizedString(zh_tw="增强免疫力", en="Boost Immunity")
                    ),
                    QuestionOption(
                        value="skin_health",
                        label=LocalizedString(zh_tw="皮肤健康", en="Skin Health")
                    ),
                ]
            ),
            Question(
                id="q2",
                type="multi",
                required=True,
                label=LocalizedString(
                    zh_tw="您有哪些过敏症状？（可多选）",
                    en="Do you have any allergies? (Multiple selection)"
                ),
                options=[
                    QuestionOption(
                        value="shellfish",
                        label=LocalizedString(zh_tw="贝类", en="Shellfish")
                    ),
                    QuestionOption(
                        value="nuts",
                        label=LocalizedString(zh_tw="坚果", en="Nuts")
                    ),
                    QuestionOption(
                        value="dairy",
                        label=LocalizedString(zh_tw="乳制品", en="Dairy")
                    ),
                    QuestionOption(
                        value="gluten",
                        label=LocalizedString(zh_tw="麸质", en="Gluten")
                    ),
                    QuestionOption(
                        value="none",
                        label=LocalizedString(zh_tw="无", en="None")
                    ),
                ]
            ),
            Question(
                id="q3",
                type="multi",
                required=False,
                label=LocalizedString(
                    zh_tw="您有哪些慢性疾病？（可多选）",
                    en="Do you have any chronic conditions? (Multiple selection)"
                ),
                options=[
                    QuestionOption(
                        value="diabetes",
                        label=LocalizedString(zh_tw="糖尿病", en="Diabetes")
                    ),
                    QuestionOption(
                        value="hypertension",
                        label=LocalizedString(zh_tw="高血压", en="Hypertension")
                    ),
                    QuestionOption(
                        value="heart_disease",
                        label=LocalizedString(zh_tw="心脏病", en="Heart Disease")
                    ),
                    QuestionOption(
                        value="thyroid",
                        label=LocalizedString(zh_tw="甲状腺疾病", en="Thyroid Disease")
                    ),
                    QuestionOption(
                        value="none",
                        label=LocalizedString(zh_tw="无", en="None")
                    ),
                ]
            ),
            Question(
                id="q4",
                type="text",
                required=False,
                label=LocalizedString(
                    zh_tw="您目前在服用哪些药物？（请列出）",
                    en="What medications are you currently taking? (Please list)"
                ),
            ),
            Question(
                id="q5",
                type="multi",
                required=True,
                label=LocalizedString(
                    zh_tw="您的饮食偏好是什么？（可多选）",
                    en="What are your dietary preferences? (Multiple selection)"
                ),
                options=[
                    QuestionOption(
                        value="vegetarian",
                        label=LocalizedString(zh_tw="素食", en="Vegetarian")
                    ),
                    QuestionOption(
                        value="vegan",
                        label=LocalizedString(zh_tw="纯素", en="Vegan")
                    ),
                    QuestionOption(
                        value="keto",
                        label=LocalizedString(zh_tw="生酮饮食", en="Keto")
                    ),
                    QuestionOption(
                        value="paleo",
                        label=LocalizedString(zh_tw="原始人饮食", en="Paleo")
                    ),
                    QuestionOption(
                        value="no_preference",
                        label=LocalizedString(zh_tw="无特殊偏好", en="No Preference")
                    ),
                ]
            ),
            Question(
                id="q6",
                type="number",
                required=True,
                label=LocalizedString(
                    zh_tw="您每月的营养品预算是多少？（人民币）",
                    en="What is your monthly budget for supplements? (CNY)"
                ),
                validation={"min": 0, "max": 10000}
            ),
        ]

        return Questionnaire(
            id="v1",
            version="1.0",
            questions=questions
        )


    def validate_answers(self, answers: List[QuestionAnswerInput]) -> ValidationResult:
        """
        验证问卷答案

        Args:
            answers: 问卷答案列表

        Returns:
            ValidationResult: 验证结果
        """
        questionnaire = self.get_questionnaire()
        errors = []

        # 构建问题映射
        questions_map = {q.id: q for q in questionnaire.questions}

        # 检查必填项
        answered_ids = {a.question_id for a in answers}
        for question in questionnaire.questions:
            if question.required and question.id not in answered_ids:
                errors.append(
                    ValidationError(
                        question_id=question.id,
                        error=f"Required field: {question.label.zh_tw}"
                    )
                )

        # 验证每个答案
        for answer in answers:
            if answer.question_id not in questions_map:
                errors.append(
                    ValidationError(
                        question_id=answer.question_id,
                        error="Unknown question"
                    )
                )
                continue

            question = questions_map[answer.question_id]

            # 验证答案类型
            if question.type == "single":
                if not isinstance(answer.value, str):
                    errors.append(
                        ValidationError(
                            question_id=answer.question_id,
                            error="Expected string value"
                        )
                    )
            elif question.type == "multi":
                if not isinstance(answer.value, list):
                    errors.append(
                        ValidationError(
                            question_id=answer.question_id,
                            error="Expected list value"
                        )
                    )
            elif question.type == "number":
                if not isinstance(answer.value, (int, float)):
                    errors.append(
                        ValidationError(
                            question_id=answer.question_id,
                            error="Expected numeric value"
                        )
                    )
                # 验证范围
                if question.validation:
                    min_val = question.validation.get("min")
                    max_val = question.validation.get("max")
                    if min_val is not None and answer.value < min_val:
                        errors.append(
                            ValidationError(
                                question_id=answer.question_id,
                                error=f"Value must be >= {min_val}"
                            )
                        )
                    if max_val is not None and answer.value > max_val:
                        errors.append(
                            ValidationError(
                                question_id=answer.question_id,
                                error=f"Value must be <= {max_val}"
                            )
                        )
            elif question.type == "text":
                if not isinstance(answer.value, str):
                    errors.append(
                        ValidationError(
                            question_id=answer.question_id,
                            error="Expected string value"
                        )
                    )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def submit_answers(
        self, user_id: UUID, answers: List[QuestionAnswerInput]
    ) -> RecommendationSessionResponse:
        """
        提交问卷答案

        Args:
            user_id: 用户 ID
            answers: 问卷答案列表

        Returns:
            RecommendationSessionResponse: 推荐会话响应

        Raises:
            ValueError: 如果验证失败或用户不存在
        """
        # 验证答案
        validation_result = self.validate_answers(answers)
        if not validation_result.valid:
            error_msg = "; ".join([f"{e.question_id}: {e.error}" for e in validation_result.errors])
            raise ValueError(f"Validation failed: {error_msg}")

        # 检查用户是否存在
        user = await self.db.execute(select(User).where(User.id == user_id))
        user_obj = user.scalar_one_or_none()
        if not user_obj:
            raise ValueError(f"User {user_id} not found")

        # 获取或创建健康档案
        health_profile_result = await self.db.execute(
            select(HealthProfile).where(HealthProfile.user_id == user_id)
        )
        health_profile = health_profile_result.scalar_one_or_none()

        if not health_profile:
            health_profile = HealthProfile(user_id=user_id)
            self.db.add(health_profile)
            await self.db.flush()

        # 保存问卷答案
        for answer in answers:
            question_answer = QuestionAnswer(
                health_profile_id=health_profile.id,
                question_id=answer.question_id,
                value={"value": answer.value}  # 存储为 JSON
            )
            self.db.add(question_answer)

        # 更新健康档案（从答案中提取关键信息）
        answers_map = {a.question_id: a.value for a in answers}

        if "q1" in answers_map:
            health_profile.goals = answers_map["q1"] if isinstance(answers_map["q1"], list) else [answers_map["q1"]]
        if "q2" in answers_map:
            allergies = answers_map["q2"] if isinstance(answers_map["q2"], list) else [answers_map["q2"]]
            health_profile.allergies = [a for a in allergies if a != "none"]
        if "q3" in answers_map:
            conditions = answers_map["q3"] if isinstance(answers_map["q3"], list) else [answers_map["q3"]]
            health_profile.chronic_conditions = [c for c in conditions if c != "none"]
        if "q4" in answers_map:
            health_profile.medications = [answers_map["q4"]] if answers_map["q4"] else []
        if "q5" in answers_map:
            health_profile.dietary_preferences = answers_map["q5"] if isinstance(answers_map["q5"], list) else [answers_map["q5"]]
        if "q6" in answers_map:
            health_profile.budget_max = answers_map["q6"]

        await self.db.flush()

        # 创建推荐会话
        recommendation_session = RecommendationSession(
            user_id=user_id,
            health_profile_id=health_profile.id,
            status="PENDING"
        )
        self.db.add(recommendation_session)
        await self.db.flush()

        await self.db.commit()

        return RecommendationSessionResponse(
            session_id=str(recommendation_session.id),
            created_at=recommendation_session.created_at
        )
