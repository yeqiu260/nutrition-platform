"""推荐引擎服务 - Perplexity AI 推荐生成
推荐服务生成模块
包含 AI 推荐逻辑 (使用 xAI Grok)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.services.rule_engine import (
    HealthProfile as RuleHealthProfile,
    NutrientCandidate,
    RuleAction,
    RuleEngine,
    SafetyInfo as RuleSafetyInfo,
)
from app.services.scoring_engine import (
    hybrid_scoring_engine,
    NutrientScore,
)
from app.services.scoring_engine import (
    hybrid_scoring_engine,
    NutrientScore,
)
# 使用 xAI Grok API (通过 OpenAI 兼容模式)

settings = get_settings()
logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型定义
# ============================================================================

class LocalizedString(BaseModel):
    """本地化字符串"""
    zh_tw: str
    en: str


class DrugInteractionInfo(BaseModel):
    """用药交互信息"""
    drug: str
    nutrient: str
    severity: str
    description: str


class SafetyInfo(BaseModel):
    """安全信息"""
    warnings: List[str] = Field(default_factory=list)
    requires_professional_consult: bool = False
    interactions: List[DrugInteractionInfo] = Field(default_factory=list)


class CommerceSlot(BaseModel):
    """商品卡位"""
    type: str  # "shopify" | "partner" | "none"
    product_id: Optional[str] = None
    offer_id: Optional[str] = None


class RecommendationItem(BaseModel):
    """推荐项"""
    rank: int = Field(..., ge=1, le=5)
    rec_key: str
    name: LocalizedString
    why: List[str] = Field(..., min_length=3, max_length=5)
    safety: SafetyInfo
    confidence: int = Field(..., ge=0, le=100)
    commerce_slot: CommerceSlot
    
    @field_validator("why")
    @classmethod
    def validate_why_length(cls, v: List[str]) -> List[str]:
        """验证 why 数组长度在 3-5 之间"""
        if len(v) < 3:
            raise ValueError("why must have at least 3 reasons")
        if len(v) > 5:
            raise ValueError("why must have at most 5 reasons")
        return v
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: int) -> int:
        """验证 confidence 在 0-100 之间"""
        if v < 0 or v > 100:
            raise ValueError("confidence must be between 0 and 100")
        return v


class RecommendationResult(BaseModel):
    """推荐结果"""
    session_id: str
    generated_at: datetime
    items: List[RecommendationItem]
    disclaimer: str
    requires_review: bool = False
    
    @field_validator("items")
    @classmethod
    def validate_items_count(cls, v: List[RecommendationItem]) -> List[RecommendationItem]:
        """验证推荐项数量恰好为 5"""
        if len(v) != 5:
            raise ValueError(f"Must have exactly 5 recommendations, got {len(v)}")
        return v
    
    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer_not_empty(cls, v: str) -> str:
        """验证免责声明非空"""
        if not v or not v.strip():
            raise ValueError("disclaimer must not be empty")
        return v


@dataclass
class HealthProfile:
    """健康档案（用于推荐引擎）"""
    user_id: str
    allergies: List[str] = field(default_factory=list)
    chronic_conditions: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    dietary_preferences: List[str] = field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    lab_metrics: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# 免责声明
# ============================================================================

DISCLAIMER_ZH = """
【健康免责声明】
本平台提供的营养建议仅供参考，不构成医疗诊断或治疗建议。
在开始任何营养补充计划之前，请咨询您的医生或专业医疗人员。
如果您正在服用药物或有任何健康状况，请务必在使用任何补充剂之前寻求专业医疗建议。
本平台不对因使用这些建议而产生的任何后果承担责任。
""".strip()

DISCLAIMER_EN = """
[Health Disclaimer]
The nutritional recommendations provided by this platform are for reference only and do not constitute medical diagnosis or treatment advice.
Please consult your doctor or healthcare professional before starting any nutritional supplement program.
If you are taking medications or have any health conditions, be sure to seek professional medical advice before using any supplements.
This platform is not responsible for any consequences arising from the use of these recommendations.
""".strip()


# ============================================================================
# 营养素知识库
# ============================================================================

NUTRIENT_DATABASE: Dict[str, Dict[str, Any]] = {
    "vitamin_d": {
        "name": LocalizedString(zh_tw="维生素D", en="Vitamin D"),
        "benefits": ["骨骼健康", "免疫支持", "情绪调节"],
        "goals": ["immunity", "bone_health", "energy"],
    },
    "omega_3": {
        "name": LocalizedString(zh_tw="Omega-3 鱼油", en="Omega-3 Fish Oil"),
        "benefits": ["心血管健康", "大脑功能", "抗炎"],
        "goals": ["heart_health", "brain_health", "immunity"],
    },
    "vitamin_c": {
        "name": LocalizedString(zh_tw="维生素C", en="Vitamin C"),
        "benefits": ["免疫支持", "抗氧化", "皮肤健康"],
        "goals": ["immunity", "skin_health", "energy"],
    },
    "vitamin_b_complex": {
        "name": LocalizedString(zh_tw="维生素B群", en="Vitamin B Complex"),
        "benefits": ["能量代谢", "神经系统", "红血球生成"],
        "goals": ["energy", "muscle_gain", "brain_health"],
    },
    "magnesium": {
        "name": LocalizedString(zh_tw="镁", en="Magnesium"),
        "benefits": ["肌肉放松", "睡眠质量", "心脏健康"],
        "goals": ["sleep", "muscle_gain", "heart_health"],
    },
    "zinc": {
        "name": LocalizedString(zh_tw="锌", en="Zinc"),
        "benefits": ["免疫功能", "伤口愈合", "皮肤健康"],
        "goals": ["immunity", "skin_health", "muscle_gain"],
    },
    "probiotics": {
        "name": LocalizedString(zh_tw="益生菌", en="Probiotics"),
        "benefits": ["肠道健康", "免疫支持", "消化功能"],
        "goals": ["immunity", "weight_loss", "energy"],
    },
    "collagen": {
        "name": LocalizedString(zh_tw="胶原蛋白", en="Collagen"),
        "benefits": ["皮肤弹性", "关节健康", "头发指甲"],
        "goals": ["skin_health", "bone_health"],
    },
    "coq10": {
        "name": LocalizedString(zh_tw="辅酶Q10", en="CoQ10"),
        "benefits": ["心脏健康", "能量产生", "抗氧化"],
        "goals": ["heart_health", "energy"],
    },
    "iron": {
        "name": LocalizedString(zh_tw="铁", en="Iron"),
        "benefits": ["血红蛋白生成", "能量水平", "认知功能"],
        "goals": ["energy", "immunity"],
    },
    "calcium": {
        "name": LocalizedString(zh_tw="钙", en="Calcium"),
        "benefits": ["骨骼健康", "肌肉功能", "神经传导"],
        "goals": ["bone_health", "muscle_gain"],
    },
    "vitamin_e": {
        "name": LocalizedString(zh_tw="维生素E", en="Vitamin E"),
        "benefits": ["抗氧化", "皮肤健康", "免疫支持"],
        "goals": ["skin_health", "immunity"],
    },
    "turmeric": {
        "name": LocalizedString(zh_tw="姜黄素", en="Turmeric/Curcumin"),
        "benefits": ["抗炎", "关节健康", "抗氧化"],
        "goals": ["immunity", "bone_health"],
    },
    "melatonin": {
        "name": LocalizedString(zh_tw="褪黑素", en="Melatonin"),
        "benefits": ["睡眠调节", "抗氧化", "免疫支持"],
        "goals": ["sleep", "immunity"],
    },
    "protein_powder": {
        "name": LocalizedString(zh_tw="蛋白粉", en="Protein Powder"),
        "benefits": ["肌肉生长", "饱腹感", "运动恢复"],
        "goals": ["muscle_gain", "weight_loss"],
    },
}


# ============================================================================
# GLM-4 推荐 Prompt 模板
# ============================================================================

RECOMMENDATION_PROMPT_TEMPLATE = """你是一位专业的营养师助手。请根据用户的健康档案生成个性化的营养补充建议。

## 用户健康档案

- 健康目标: {goals}
- 过敏原: {allergies}
- 慢性疾病: {chronic_conditions}
- 正在服用的药物: {medications}
- 饮食偏好: {dietary_preferences}
- 预算范围: {budget}
{lab_metrics_section}

## 可选营养素列表

{available_nutrients}

## 要求

1. 从可选营养素列表中选择最适合用户的 5 种营养素
2. 对于每种营养素，提供 3-5 条推荐原因（Why），连结到用户的目标、饮食或化验指标
3. 对于每种营养素，评估安全性并提供警告（如有）
4. 对于每种营养素，给出信心分数（0-100）
5. 按推荐优先级排序（1 最高，5 最低）

## 输出格式

请以 JSON 格式返回，格式如下：
```json
{{
    "recommendations": [
        {{
            "rank": 1,
            "rec_key": "营养素键名",
            "why": ["原因1", "原因2", "原因3"],
            "confidence": 85,
            "safety_notes": ["安全提示（如有）"]
        }}
    ]
}}
```

注意：
- 必须返回恰好 5 个推荐
- why 必须有 3-5 条原因
- confidence 必须在 0-100 之间
- 只返回 JSON，不要有其他文字
- 考虑用户的过敏和用药情况，避免推荐可能有风险的营养素
"""

LAB_METRICS_SECTION_TEMPLATE = """
- 化验指标:
{metrics}
"""

# 个性化推荐理由 Prompt 模板
PERSONALIZED_WHY_PROMPT_TEMPLATE = """你是一位专业且亲切的营养师。请为用户生成关于「{nutrient_name}」的个性化推荐理由。

## 用户资料
- 健康目标: {goals}
- 饮食偏好: {dietary_preferences}
{lab_summary}

## 已知信息
{base_reasons}

## 营养素功效
{nutrient_benefits}

## 要求
1. 生成恰好 3 条推荐理由
2. 每条理由 25-50 字
3. 语气亲切专业，像营养师面对面建议
4. 必须结合用户具体情况（目标、饮食、指标）
5. 避免使用「您的健康目标」这种机械表述
6. 让用户感受到这是为他量身定制的建议

## 输出格式
只返回 JSON 数组，不要有其他文字：
["理由1", "理由2", "理由3"]

示例输出：
["维他命D是许多人普遍缺乏的关键营养素，尤其适合日照不足的现代人。", "它不仅是骨骼健康的基石，更在调节免疫系统上扮演核心角色。", "根据您关注的免疫力和骨骼健康，维他命D是高性价比的基础选择。"]
"""


# ============================================================================
# 推荐引擎实现
# ============================================================================

class RecommendationEngine:
    """
    推荐引擎 - 基于 GLM-4 生成个性化营养建议
    
    实现需求：
    - 4.1: 生成恰好 5 个营养推荐
    - 4.5: 每个推荐项提供 3-5 条原因
    - 4.6: 每个推荐项提供安全提示
    - 4.7: 每个推荐项提供信心分数（0-100）
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化推荐引擎
        
        Args:
            api_key: Perplexity API Key，如果不提供则从配置读取
        """
        self.api_key = api_key or settings.grok_api_key
        self._client = None
        self.rule_engine = RuleEngine()
        self.nutrient_db = NUTRIENT_DATABASE
    
    @property
    def client(self):
        """Lazy load xAI Grok client"""
        if self._client is None:
            if settings.grok_api_key:
                try:
                    from openai import OpenAI
                    self._client = OpenAI(
                        api_key=settings.grok_api_key,
                        base_url="https://api.x.ai/v1"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize Grok client: {e}")
                    self._client = None
        return self._client
    
    def _build_health_profile_for_rules(
        self, profile: HealthProfile
    ) -> RuleHealthProfile:
        """
        将健康档案转换为规则引擎格式
        
        Args:
            profile: 健康档案
            
        Returns:
            RuleHealthProfile: 规则引擎格式的健康档案
        """
        return RuleHealthProfile(
            allergies=profile.allergies,
            chronic_conditions=profile.chronic_conditions,
            medications=profile.medications,
            goals=profile.goals,
            dietary_preferences=profile.dietary_preferences,
            lab_metrics=profile.lab_metrics,
        )
    
    def _get_available_nutrients(
        self, profile: HealthProfile
    ) -> List[NutrientCandidate]:
        """
        获取可用的营养素候选列表（已过滤被阻挡的）
        
        Args:
            profile: 健康档案
            
        Returns:
            List[NutrientCandidate]: 可用的营养素候选列表
        """
        rule_profile = self._build_health_profile_for_rules(profile)
        
        # 为所有营养素创建候选
        candidates = []
        for rec_key, info in self.nutrient_db.items():
            # 计算基础分数（基于目标匹配度）
            base_score = self._calculate_base_score(rec_key, profile)
            candidates.append(NutrientCandidate(nutrient=rec_key, base_score=base_score))
        
        # 应用规则引擎过滤和调整权重
        filtered_candidates = self.rule_engine.filter_and_rank_candidates(
            rule_profile, candidates
        )
        
        return filtered_candidates
    
    def _calculate_base_score(self, rec_key: str, profile: HealthProfile) -> float:
        """
        计算营养素的基础分数（用于回退方案）
        
        Args:
            rec_key: 营养素键名
            profile: 健康档案
            
        Returns:
            float: 基础分数 (0-100)
        """
        if rec_key not in self.nutrient_db:
            return 0.0
        
        nutrient_info = self.nutrient_db[rec_key]
        nutrient_goals = nutrient_info.get("goals", [])
        
        # 计算目标匹配度
        matching_goals = set(profile.goals) & set(nutrient_goals)
        goal_score = len(matching_goals) * 20  # 每个匹配目标 20 分
        
        # 基础分数
        base = 50.0
        
        return min(100.0, base + goal_score)
    
    def _generate_fallback_recommendations(
        self, profile: HealthProfile, candidates: List[NutrientCandidate]
    ) -> List[RecommendationItem]:
        """
        生成回退推荐（当 LLM 调用失败时使用）
        
        Args:
            profile: 健康档案
            candidates: 可用的营养素候选列表
            
        Returns:
            List[RecommendationItem]: 回退推荐列表
        """
        # 取前 5 个候选
        top_candidates = candidates[:5]
        
        # 如果候选不足 5 个，从数据库补充
        if len(top_candidates) < 5:
            existing_keys = {c.nutrient for c in top_candidates}
            for rec_key in self.nutrient_db:
                if rec_key not in existing_keys:
                    top_candidates.append(
                        NutrientCandidate(nutrient=rec_key, base_score=50.0)
                    )
                if len(top_candidates) >= 5:
                    break
        
        recommendations = []
        for i, candidate in enumerate(top_candidates[:5]):
            rec_key = candidate.nutrient
            
            if rec_key in self.nutrient_db:
                info = self.nutrient_db[rec_key]
                name = info["name"]
                benefits = info.get("benefits", [])
            else:
                name = LocalizedString(zh_tw=rec_key, en=rec_key)
                benefits = []
            
            # 生成 why 原因
            why = []
            if benefits:
                why.extend([f"有助于{b}" for b in benefits[:3]])
            if len(why) < 3:
                why.extend([
                    "根据您的健康目标推荐",
                    "有助于整体健康",
                    "适合您的饮食习惯",
                ][:3 - len(why)])
            
            # 获取安全信息
            rule_profile = self._build_health_profile_for_rules(profile)
            safety_check = self.rule_engine.check_nutrient(rec_key, rule_profile)
            
            safety = SafetyInfo(
                warnings=safety_check.warnings,
                requires_professional_consult=len(safety_check.warnings) > 0,
                interactions=[],
            )
            
            recommendations.append(RecommendationItem(
                rank=i + 1,
                rec_key=rec_key,
                name=name,
                why=why[:5],
                safety=safety,
                confidence=int(candidate.base_score),
                commerce_slot=CommerceSlot(type="none"),
            ))
        
        return recommendations
    
    async def _generate_personalized_why(
        self,
        nutrient: str,
        profile: HealthProfile,
        base_reasons: List[str]
    ) -> List[str]:
        """
        使用 AI 生成个性化推荐理由
        
        Args:
            nutrient: 营养素键名
            profile: 健康档案
            base_reasons: 基础评分理由
            
        Returns:
            List[str]: 个性化推荐理由（3 条）
        """
        if not self.api_key:
            return base_reasons[:3] if len(base_reasons) >= 3 else base_reasons + ["有助于整体健康"] * (3 - len(base_reasons))
        
        try:
            # 获取营养素信息
            nutrient_info = self.nutrient_db.get(nutrient, {})
            nutrient_name = nutrient_info.get("name", LocalizedString(zh_tw=nutrient, en=nutrient)).zh_tw
            nutrient_benefits = nutrient_info.get("benefits", [])
            
            # 构建健康指标摘要
            lab_summary = ""
            if profile.lab_metrics:
                abnormal_metrics = [
                    f"{m.get('name', 'Unknown')}: {m.get('value')} ({m.get('flag', 'normal')})"
                    for m in profile.lab_metrics
                    if m.get('flag', 'normal').lower() in ['low', 'high']
                ]
                if abnormal_metrics:
                    lab_summary = f"- 健康指标异常项: {', '.join(abnormal_metrics[:3])}"
            
            # 构建 prompt
            prompt = PERSONALIZED_WHY_PROMPT_TEMPLATE.format(
                nutrient_name=nutrient_name,
                goals=", ".join(profile.goals) if profile.goals else "未指定",
                dietary_preferences=", ".join(profile.dietary_preferences) if profile.dietary_preferences else "无特殊偏好",
                lab_summary=lab_summary if lab_summary else "- 健康指标: 暂未提供报告",
                base_reasons="\n".join([f"- {r}" for r in base_reasons]) if base_reasons else "无",
                nutrient_benefits=", ".join(nutrient_benefits) if nutrient_benefits else "综合营养支持"
            )
            
            # 调用 AI
            response = self.client.chat.completions.create(
                model="grok-4-1-fast-reasoning",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # 提高创意性
                max_tokens=300,
            )
            
            content = response.choices[0].message.content.strip()
            
            # 解析 JSON 数组
            # 尝试提取 JSON 部分
            if content.startswith("["):
                reasons = json.loads(content)
            else:
                # 可能有 markdown 包裹
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    reasons = json.loads(json_match.group())
                else:
                    logger.warning(f"Failed to parse AI response: {content[:100]}")
                    return base_reasons[:3] if len(base_reasons) >= 3 else base_reasons + ["有助于整体健康"] * (3 - len(base_reasons))
            
            # 验证结果
            if isinstance(reasons, list) and len(reasons) >= 3:
                logger.info(f"Generated personalized why for {nutrient}: {reasons[:3]}")
                return reasons[:3]
            else:
                logger.warning(f"Invalid AI response format: {reasons}")
                return base_reasons[:3] if len(base_reasons) >= 3 else base_reasons + ["有助于整体健康"] * (3 - len(base_reasons))
                
        except Exception as e:
            logger.error(f"Failed to generate personalized why for {nutrient}: {e}")
            # 回退到基础理由
            return base_reasons[:3] if len(base_reasons) >= 3 else base_reasons + ["有助于整体健康"] * (3 - len(base_reasons))
    
    async def _generate_report_interpretation(self, profile: HealthProfile) -> Optional[str]:
        """
        生成 AI 报告解读（只用一个，不是一个成分一个）
        
        Args:
            profile: 健康档案
            
        Returns:
            Optional[str]: AI 报告解读文本
        """
        if not profile.lab_metrics or not self.api_key:
            return None
        
        try:
            # 构建报告解读 prompt
            metrics_text = "\n".join([
                f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')} {m.get('unit', '')} ({m.get('flag', 'normal')})"
                for m in profile.lab_metrics
            ])
            
            prompt = f"""您是一位专业的健康顾问。请根据以下体检报告数据，提供一个简洁的整体健康评估和建议。

体检指标：
{metrics_text}

请提供：
1. 整体健康状况评估（2-3 句话）
2. 主要关注点（如有异常指标）
3. 生活方式建议（2-3 条）

请用简洁、易懂的语言，不要超过 200 字。"""

            # 调用 AI 解释报告
            response = self.client.chat.completions.create(
                model="grok-4-1-fast-reasoning",
                messages=[
                    {"role": "system", "content": "你是一个专业的营养师，负责解读体检报告并给出简短的健康建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500,
            )
            
            interpretation = response.choices[0].message.content.strip()
            logger.info(f"Generated report interpretation: {interpretation[:100]}...")
            return interpretation
            
        except Exception as e:
            logger.error(f"Failed to generate report interpretation: {e}")
            return None
    
    async def generate(
        self,
        session_id: str,
        profile: HealthProfile,
    ) -> RecommendationResult:
        """
        生成推荐（使用混合评分算法）
        
        Args:
            session_id: 推荐会话 ID
            profile: 健康档案
            
        Returns:
            RecommendationResult: 推荐结果
        """
        recommendations = []
        requires_review = False
        
        logger.info("Using hybrid scoring algorithm (0.7 report + 0.3 questionnaire)")
        try:
            # 1. 使用混合评分引擎计算分数
            top_nutrients = hybrid_scoring_engine.get_top_n(
                goals=profile.goals,
                dietary_preferences=profile.dietary_preferences,
                lab_metrics=profile.lab_metrics,
                budget_max=profile.budget_max,
                n=10,  # 先获取 top 10，然后应用规则引擎过滤
            )
            
            # 2. 应用规则引擎过滤（安全护栏）
            rule_profile = self._build_health_profile_for_rules(profile)
            filtered_nutrients = []
            
            for nutrient_score in top_nutrients:
                # 检查安全性
                safety_check = self.rule_engine.check_nutrient(
                    nutrient_score.nutrient, rule_profile
                )
                
                if safety_check.safe or safety_check.warnings:
                    # 允许或警告的营养素
                    filtered_nutrients.append((nutrient_score, safety_check))
                else:
                    # 被阻挡的营养素
                    logger.info(f"Nutrient {nutrient_score.nutrient} blocked: {safety_check.blocked_by}")
            
            # 3. 取前 5 个
            top_5 = filtered_nutrients[:5]
            
            # 4. 如果不足 5 个，从剩余候选中补充
            if len(top_5) < 5:
                remaining = [n for n in top_nutrients if n.nutrient not in [t[0].nutrient for t in top_5]]
                for nutrient_score in remaining:
                    if len(top_5) >= 5:
                        break
                    safety_check = self.rule_engine.check_nutrient(
                        nutrient_score.nutrient, rule_profile
                    )
                    if not safety_check.blocked_by:
                        top_5.append((nutrient_score, safety_check))
            
            # 5. 构建推荐项
            for i, (nutrient_score, safety_check) in enumerate(top_5):
                rec_key = nutrient_score.nutrient
                
                # 获取营养素名称
                if rec_key in self.nutrient_db:
                    name = self.nutrient_db[rec_key]["name"]
                else:
                    name = LocalizedString(zh_tw=rec_key, en=rec_key)
                
                # 使用 AI 生成个性化推荐理由
                base_reasons = nutrient_score.reasons[:5]  # 基础评分理由
                why = await self._generate_personalized_why(rec_key, profile, base_reasons)
                
                # 构建安全信息
                safety = SafetyInfo(
                    warnings=safety_check.warnings,
                    requires_professional_consult=len(safety_check.warnings) > 0,
                    interactions=[],
                )
                
                # 信心分数基于最终分数
                confidence = int(min(100, max(0, nutrient_score.final_score)))
                
                recommendations.append(RecommendationItem(
                    rank=i + 1,
                    rec_key=rec_key,
                    name=name,
                    why=why,
                    safety=safety,
                    confidence=confidence,
                    commerce_slot=CommerceSlot(type="none"),
                ))
            
            # 6. 生成 AI 报告解读（如果有报告数据）
            if profile.lab_metrics and self.api_key:
                report_interpretation = await self._generate_report_interpretation(profile)
            
            logger.info(f"Generated {len(recommendations)} recommendations using hybrid scoring")
            
        except Exception as e:
            logger.error(f"Hybrid scoring failed: {e}, falling back to rule engine")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # 回退到规则引擎
            candidates = self._get_available_nutrients(profile)
            recommendations = self._generate_fallback_recommendations(profile, candidates)
        
        # 重新排序
        recommendations.sort(key=lambda x: x.rank)
        for i, rec in enumerate(recommendations):
            rec.rank = i + 1
        
        # 检查是否需要人工审核（基于用户健康状况复杂度）
        if (
            len(profile.medications) > 2 or
            len(profile.chronic_conditions) > 1 or
            any(r.safety.requires_professional_consult for r in recommendations)
        ):
            requires_review = True
        
        return RecommendationResult(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            items=recommendations,
            disclaimer=DISCLAIMER_ZH,
            requires_review=requires_review,
        )
    
    def generate_sync(
        self,
        session_id: str,
        profile: HealthProfile,
    ) -> RecommendationResult:
        """
        同步生成推荐（使用混合评分算法，不使用 LLM）
        
        Args:
            session_id: 推荐会话 ID
            profile: 健康档案
            
        Returns:
            RecommendationResult: 推荐结果
        """
        # 使用混合评分引擎
        top_nutrients = hybrid_scoring_engine.get_top_n(
            goals=profile.goals,
            dietary_preferences=profile.dietary_preferences,
            lab_metrics=profile.lab_metrics,
            budget_max=profile.budget_max,
            n=10,
        )
        
        # 应用规则引擎过滤
        rule_profile = self._build_health_profile_for_rules(profile)
        filtered_nutrients = []
        
        for nutrient_score in top_nutrients:
            safety_check = self.rule_engine.check_nutrient(
                nutrient_score.nutrient, rule_profile
            )
            if safety_check.safe or safety_check.warnings:
                filtered_nutrients.append((nutrient_score, safety_check))
        
        # 取前 5 个并构建推荐项
        recommendations = []
        for i, (nutrient_score, safety_check) in enumerate(filtered_nutrients[:5]):
            rec_key = nutrient_score.nutrient
            
            if rec_key in self.nutrient_db:
                name = self.nutrient_db[rec_key]["name"]
            else:
                name = LocalizedString(zh_tw=rec_key, en=rec_key)
            
            why = nutrient_score.reasons[:5]
            if len(why) < 3:
                why.extend([
                    "根据您的健康档案推荐",
                    "有助于整体健康",
                    "适合您的需求",
                ][:3 - len(why)])
            
            safety = SafetyInfo(
                warnings=safety_check.warnings,
                requires_professional_consult=len(safety_check.warnings) > 0,
                interactions=[],
            )
            
            recommendations.append(RecommendationItem(
                rank=i + 1,
                rec_key=rec_key,
                name=name,
                why=why,
                safety=safety,
                confidence=int(min(100, max(0, nutrient_score.final_score))),
                commerce_slot=CommerceSlot(type="none"),
            ))
        
        # 检查是否需要人工审核
        requires_review = (
            len(profile.medications) > 2 or
            len(profile.chronic_conditions) > 1 or
            any(r.safety.requires_professional_consult for r in recommendations)
        )
        
        return RecommendationResult(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            items=recommendations,
            disclaimer=DISCLAIMER_ZH,
            requires_review=requires_review,
        )


# ============================================================================
# 辅助函数
# ============================================================================

def create_recommendation_engine(api_key: Optional[str] = None) -> RecommendationEngine:
    """
    创建推荐引擎实例
    
    Args:
        api_key: 可选的 API Key
        
    Returns:
        RecommendationEngine 实例
    """
    return RecommendationEngine(api_key=api_key)


def get_disclaimer(locale: str = "zh-TW") -> str:
    """
    获取免责声明
    
    Args:
        locale: 语言代码
        
    Returns:
        str: 免责声明文本
    """
    if locale.lower() in ["en", "en-us", "en-gb"]:
        return DISCLAIMER_EN
    return DISCLAIMER_ZH
