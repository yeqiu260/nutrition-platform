"""
问卷调查 API 模块
处理问卷提交、评分和推荐生成 (使用 xAI Grok 推荐)
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_maker, get_db
from app.core.auth_deps import get_current_user_optional
from app.models.admin import SystemConfig
from app.models.product import Product
from app.models.user import User
from app.models.user_history import QuizHistory
from app.middleware.endpoint_limit import rate_limit
from app.services.usage_tracker import usage_tracker
from app.services.security_compliance import encryption_service

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

# Grok API 并发控制 - 限制同时只能有 1 个请求
_grok_semaphore = asyncio.Semaphore(1)

# ============================================================================
# 查询使用量 API
# ============================================================================

@router.get("/usage")
async def get_usage(request: Request, db: AsyncSession = Depends(get_db)):
    """
    查询当前用户今天的 AI 使用量
    
    返回：
    - used: 已使用次数
    - remaining: 剩余次数
    - limit: 每日限制
    - reset_at: 重置时间
    """
    # 优先使用 X-User-ID 请求头进行用户标识，否则回退到 IP 地址
    user_identifier = request.headers.get("X-User-ID")
    if not user_identifier:
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        user_identifier = client_ip
    
    usage_info = await usage_tracker.get_usage(db, user_identifier)
    
    return {
        "success": True,
        "data": usage_info
    }


# ============================================================================
# 请求/响应模型
# ============================================================================

class QuizAnswer(BaseModel):
    """单个问卷答案"""
    supplement_id: str = Field(..., description="补充品 ID")
    supplement_name: str = Field(..., description="补充品名称")
    group: str = Field(..., description="分类")
    screen_score: int = Field(..., description="筛选阶段分数")
    detail_score: int = Field(..., description="详细阶段分数")
    total_score: int = Field(..., description="总分")
    level: str = Field(..., description="等级: high/medium/low/none")


class QuizSubmitRequest(BaseModel):
    """问卷提交请求"""
    answers: List[QuizAnswer] = Field(..., description="所有补充品的答案")
    top_results: List[QuizAnswer] = Field(..., description="前3个高分结果")
    health_data: Optional[Dict[str, Any]] = Field(None, description="体检报告提取的健康数据")


class RecommendationReason(BaseModel):
    """推荐原因"""
    text: str


class SafetyWarning(BaseModel):
    """安全警告"""
    text: str


class ProductRecommendation(BaseModel):
    """商品推荐"""
    product_id: str = Field(..., description="商品 ID")
    product_name: str = Field(..., description="商品名称")
    why_this_product: List[str] = Field(..., description="为什么推荐这个商品（2-3条）")
    price: Optional[float] = None
    currency: str = "TWD"
    purchase_url: str = Field(..., description="购买链接")
    image_url: Optional[str] = None
    partner_name: Optional[str] = None


class QuizRecommendationItem(BaseModel):
    """问卷推荐项"""
    rank: int = Field(..., description="排名 1-3")
    supplement_id: str = Field(..., description="补充品 ID")
    name: str = Field(..., description="补充品名称")
    group: str = Field(..., description="分类")
    why: List[str] = Field(..., description="推荐原因 3-5 条")
    safety: List[str] = Field(default_factory=list, description="安全提示")
    confidence: int = Field(..., description="信心分数 0-100")
    recommended_products: List[ProductRecommendation] = Field(default_factory=list, description="AI 推荐的商品")


class QuizRecommendationResponse(BaseModel):
    """问卷推荐响应"""
    session_id: str = Field(..., description="会话 ID")
    generated_at: datetime = Field(..., description="生成时间")
    items: List[QuizRecommendationItem] = Field(..., description="推荐项列表")
    disclaimer: str = Field(..., description="免责声明")
    ai_generated: bool = Field(default=True, description="是否由 AI 生成")
    based_on_lab_report: bool = Field(default=False, description="是否基于体检报告")


# ============================================================================
# Grok Prompt 模板
# ============================================================================

# 无体检报告时的 Prompt
QUIZ_RECOMMENDATION_PROMPT_NO_LAB = """你是一位专业的营养学专家。根据用户的问卷答案，推荐3个最适合的补充品。

对于每个推荐的补充品，从可用商品中选择最合适的1-2个商品，并提供具体的推荐理由。

用户问卷结果：
{quiz_results}

可用商品（按补充品分类）：
{available_products}

推荐标准：
1. 选择最适合用户需求的补充品（综合考虑分数和用户情况）
2. 为每个补充品选择最合适的1-2个商品（考虑描述、价格、品牌）
3. 为每个商品提供2-3条具体的推荐理由

推荐理由要求：
- 引用用户的问卷评分（如"问卷评分5分，为中等需求"）
- 说明补充品的主要功效
- 结合用户的需求分类给出建议

【重要】你必须只返回JSON格式的数据，不要有任何其他文字、解释或说明。格式如下：
{{
  "recommendations": [
    {{
      "rank": 1,
      "supplement_id": "vitamin_d",
      "why": ["问卷评分5分，为中等需求，需优先补充以维持骨骼健康", "分类为基础营养 | 骨骼与免疫，适合日常阳光不足或免疫需求者", "中等水平补充可预防缺乏导致的疲劳与骨质问题"],
      "confidence": 85,
      "recommended_products": [
        {{
          "product_id": "商品UUID",
          "why_this_product": ["推荐理由1", "推荐理由2", "推荐理由3"]
        }}
      ]
    }}
  ]
}}

注意：
- supplement_id 必须与问卷结果中的 ID 完全匹配
- product_id 必须与可用商品列表中的 ID 完全匹配
- 每个推荐理由要具体、实用、易懂
- 只返回JSON，不要有任何其他文字"""


# 有体检报告时的 Prompt（强调引用具体化验值）
QUIZ_RECOMMENDATION_PROMPT_WITH_LAB = """你是一位专业的营养学专家。用户已上传体检报告，请优先根据体检数据结合问卷答案，推荐3个最适合的补充品。

对于每个推荐的补充品，从可用商品中选择最合适的1-2个商品，并提供具体的推荐理由。

用户问卷结果：
{quiz_results}

可用商品（按补充品分类）：
{available_products}

{lab_metrics_section}

【核心要求】推荐逻辑必须优先基于体检数据：
1. 优先关注异常指标：偏高或偏低的指标是推荐的首要依据
2. 推荐理由必须引用具体数值：如"您的血红蛋白为 10.9 g/dL，低于正常范围(12-16 g/dL)"
3. 问卷分数作为辅助：结合问卷分数补充说明

推荐理由格式示例（必须遵循）：
- "体检显示血红蛋白 10.9 g/dL 偏低，B群维生素（尤其是B12、叶酸）有助于红细胞生成，改善贫血"
- "体检HDL胆固醇 1.6 mg/dL 偏低，Omega-3可提升好胆固醇水平"
- "体检铁蛋白 314 ng/mL 偏高，结合问卷评分，建议关注肝脏健康"

【重要】你必须只返回JSON格式的数据，不要有任何其他文字、解释或说明。格式如下：
{{
  "recommendations": [
    {{
      "rank": 1,
      "supplement_id": "vitamin_b",
      "why": ["体检显示血红蛋白 10.9 g/dL 偏低（正常范围12-16 g/dL），B群维生素有助于红细胞生成，改善贫血", "问卷评分5分也显示中等需求，支持能量代谢与神经健康", "综合考虑低HDL（1.6 mg/dL）和贫血风险，B群可辅助整体营养平衡"],
      "confidence": 90,
      "recommended_products": [
        {{
          "product_id": "商品UUID",
          "why_this_product": ["推荐理由1", "推荐理由2", "推荐理由3"]
        }}
      ]
    }}
  ]
}}

注意：
- supplement_id 必须与问卷结果中的 ID 完全匹配
- product_id 必须与可用商品列表中的 ID 完全匹配
- 每条推荐理由必须引用至少一个具体的体检数值
- 只返回JSON，不要有任何其他文字"""


LAB_METRICS_SECTION_TEMPLATE = """## 【重要】用户真实体检数据

以下是用户上传的体检报告数据，请在推荐中必须引用这些具体数值：

{metrics}

**强制要求：**
1. 异常指标（偏高或偏低）必须优先考虑
2. 每条推荐理由必须包含具体的化验数值（如"血红蛋白 10.9 g/dL"）
3. 不要只说"问卷分数X分"，要说"体检显示XX指标为XX，偏高/偏低"
"""


# ============================================================================
# 健康数据转换函数
# ============================================================================

def convert_health_data_to_lab_metrics(health_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    将体检报告提取的健康数据转换为 lab_metrics 格式
    
    Args:
        health_data: 从体检报告提取的健康数据
        
    Returns:
        List[Dict]: lab_metrics 格式的数据
    """
    # 参考范围定义
    REFERENCE_RANGES = {
        "hemoglobin": {"low": 12.0, "high": 17.0, "unit": "g/dL", "name_zh": "血红蛋白"},
        "ferritin": {"low": 30, "high": 300, "unit": "ng/mL", "name_zh": "铁蛋白"},
        "vitamin_d": {"low": 30, "high": 100, "unit": "ng/mL", "name_zh": "维生素D"},
        "vitamin_b12": {"low": 200, "high": 900, "unit": "pg/mL", "name_zh": "维生素B12"},
        "folic_acid": {"low": 3, "high": 17, "unit": "ng/mL", "name_zh": "叶酸"},
        "fasting_glucose": {"low": 70, "high": 100, "unit": "mg/dL", "name_zh": "空腹血糖"},
        "hba1c": {"low": 4.0, "high": 5.7, "unit": "%", "name_zh": "糖化血红蛋白"},
        "total_cholesterol": {"low": 125, "high": 200, "unit": "mg/dL", "name_zh": "总胆固醇"},
        "ldl": {"low": 0, "high": 100, "unit": "mg/dL", "name_zh": "低密度脂蛋白"},
        "hdl": {"low": 40, "high": 200, "unit": "mg/dL", "name_zh": "高密度脂蛋白"},
        "triglycerides": {"low": 0, "high": 150, "unit": "mg/dL", "name_zh": "甘油三酯"},
        "alt": {"low": 0, "high": 40, "unit": "U/L", "name_zh": "谷丙转氨酶"},
        "ast": {"low": 0, "high": 40, "unit": "U/L", "name_zh": "谷草转氨酶"},
        "creatinine": {"low": 0.6, "high": 1.2, "unit": "mg/dL", "name_zh": "肌酐"},
        "uric_acid": {"low": 3.5, "high": 7.2, "unit": "mg/dL", "name_zh": "尿酸"},
        "tsh": {"low": 0.4, "high": 4.0, "unit": "mIU/L", "name_zh": "促甲状腺激素"},
    }
    
    lab_metrics = []
    
    for key, value in health_data.items():
        # 跳过非数值字段
        if key in ['abnormal_findings', 'recommendations', 'overall_interpretation']:
            continue
        
        if value is None:
            continue
        
        # 获取参考范围
        ref = REFERENCE_RANGES.get(key)
        if not ref:
            continue
        
        # 判断 flag
        flag = "normal"
        if value < ref["low"]:
            flag = "low"
        elif value > ref["high"]:
            flag = "high"
        
        lab_metrics.append({
            "name": key,
            "name_zh": ref["name_zh"],
            "value": value,
            "unit": ref["unit"],
            "flag": flag,
            "reference_low": ref["low"],
            "reference_high": ref["high"],
        })
    
    return lab_metrics


# ============================================================================
# 免责声明
# ============================================================================

DISCLAIMER_ZH = """
【健康免责声明】
本測驗是根據你自填的生活與症狀資訊，做出的「風險與優先度」排序，不代表已經確診缺乏或一定需要服用補充劑。
在開始任何長期補充前，特別是涉及鐵劑、紅麴、肝臟相關、糖尿病相關產品時，建議先諮詢醫生或藥劑師，
必要時可搭配血液檢查，以獲得更精準的營養管理。
""".strip()


# ============================================================================
# API 实现
# ============================================================================

async def get_all_approved_products() -> Dict[str, List[Dict[str, Any]]]:
    """获取所有已审核的商品，按 supplement_id 分组"""
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(Product)
                .where(
                    Product.is_active == True,
                    Product.is_approved == True
                )
                .order_by(Product.sort_order.desc(), Product.created_at.desc())
            )
            products = result.scalars().all()
            
            # 按 supplement_id 分组
            products_by_supp: Dict[str, List[Dict[str, Any]]] = {}
            for p in products:
                if p.supplement_id not in products_by_supp:
                    products_by_supp[p.supplement_id] = []
                
                products_by_supp[p.supplement_id].append({
                    'id': str(p.id),
                    'name': p.name,
                    'description': p.description or '',
                    'price': p.price,
                    'currency': p.currency,
                    'partner_name': p.partner_name or '',
                    'purchase_url': p.purchase_url,
                    'image_url': p.image_url or '',
                })
            
            return products_by_supp
    except Exception as e:
        logger.error(f"Failed to fetch products: {e}")
        return {}


def _build_quiz_prompt(
    all_answers: List[QuizAnswer], 
    products_by_supp: Dict[str, List[Dict[str, Any]]],
    lab_metrics: Optional[List[Dict[str, Any]]] = None
) -> str:
    """构建问卷推荐 Prompt - 包含详细的商品信息和体检报告数据"""
    results_text = []
    
    # 发送所有问卷结果给 AI（按分数从高到低排序），让 AI 综合判断
    sorted_answers = sorted(all_answers, key=lambda x: x.total_score, reverse=True)
    top_answers = sorted_answers  # 不再限制候选池，发送全部
    
    # 构建问卷结果文本 - 包含所有补充品
    for result in top_answers:
        results_text.append(
            f"- {result.supplement_name} ({result.supplement_id}): {result.total_score}分, "
            f"等级: {result.level}, 分类: {result.group}"
        )
    
    # 构建商品列表 - 不限制分类，展示所有可用商品
    products_text = []
    relevant_supp_ids = {a.supplement_id for a in top_answers}
    
    if products_by_supp:
        for supp_id, products in products_by_supp.items():
            if supp_id in relevant_supp_ids and products:
                # 找到对应的补充品名称
                supp_name = next((a.supplement_name for a in top_answers if a.supplement_id == supp_id), supp_id)
                products_text.append(f"\n【{supp_name} ({supp_id})】")
                
                # 最多显示3个商品
                for idx, p in enumerate(products[:3], 1):
                    product_info = [
                        f"  {idx}. {p['name']} (ID: {p['id']})"
                    ]
                    
                    # 添加描述
                    if p.get('description'):
                        desc = p['description'][:100]  # 限制长度
                        product_info.append(f"     描述: {desc}")
                    
                    # 添加价格
                    if p.get('price'):
                        product_info.append(f"     价格: {p['currency']} {p['price']}")
                    
                    # 添加品牌/合作商
                    if p.get('partner_name'):
                        product_info.append(f"     品牌: {p['partner_name']}")
                    
                    products_text.append("\n".join(product_info))
    
    if not products_text:
        products_text.append("暂无可用商品")
    
    # 构建体检报告部分
    lab_metrics_section = ""
    if lab_metrics:
        metrics_text = []
        abnormal_count = 0
        for metric in lab_metrics:
            flag_emoji = ""
            if metric['flag'] == 'low':
                flag_emoji = "偏低"
                abnormal_count += 1
            elif metric['flag'] == 'high':
                flag_emoji = "偏高"
                abnormal_count += 1
            else:
                flag_emoji = "正常"
            
            metrics_text.append(
                f"- {metric['name_zh']} ({metric['name']}): {metric['value']} {metric['unit']} "
                f"【{flag_emoji}】(参考范围: {metric['reference_low']}-{metric['reference_high']})"
            )
        
        if abnormal_count > 0:
            metrics_text.insert(0, f"**发现 {abnormal_count} 项异常指标，请优先关注：**\n")
        
        lab_metrics_section = LAB_METRICS_SECTION_TEMPLATE.format(
            metrics="\n".join(metrics_text)
        )
    
    # 根据是否有化验数据选择不同的 prompt 模板
    if lab_metrics:
        # 有化验数据时，使用强调引用具体数值的 prompt
        return QUIZ_RECOMMENDATION_PROMPT_WITH_LAB.format(
            quiz_results="\n".join(results_text),
            available_products="\n".join(products_text),
            lab_metrics_section=lab_metrics_section
        )
    else:
        # 无化验数据时，使用基于问卷分数的 prompt
        return QUIZ_RECOMMENDATION_PROMPT_NO_LAB.format(
            quiz_results="\n".join(results_text),
            available_products="\n".join(products_text)
        )


def _parse_ai_response(text: str) -> List[Dict[str, Any]]:
    """解析 AI 返回的 JSON 数据"""
    # 清理响应文本
    text = text.strip()
    
    # 移除 markdown 代码块标记
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # 尝试直接解析
    try:
        parsed = json.loads(text)
        return parsed.get("recommendations", [])
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
    
    # 尝试修复不完整的 JSON（添加缺失的括号）
    try:
        # 计算括号数量
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        
        # 添加缺失的闭合括号
        fixed_text = text + ']' * open_brackets + '}' * open_braces
        parsed = json.loads(fixed_text)
        print(f"✓ Fixed incomplete JSON by adding {open_brackets} ] and {open_braces} }}")
        return parsed.get("recommendations", [])
    except json.JSONDecodeError:
        pass
    
    # 尝试提取部分有效的 JSON
    try:
        # 找到 recommendations 数组的开始
        start = text.find('"recommendations"')
        if start != -1:
            # 找到数组开始
            arr_start = text.find('[', start)
            if arr_start != -1:
                # 尝试找到完整的第一个对象
                depth = 0
                obj_start = -1
                for i, c in enumerate(text[arr_start:], arr_start):
                    if c == '{':
                        if depth == 1:
                            obj_start = i
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 1 and obj_start != -1:
                            # 找到一个完整的对象
                            obj_text = text[obj_start:i+1]
                            try:
                                obj = json.loads(obj_text)
                                print(f"✓ Extracted partial recommendation")
                                return [obj]
                            except:
                                pass
    except Exception as e:
        print(f"Partial extraction failed: {e}")
    
    raise ValueError(f"Failed to parse JSON from response: {response_text[:200]}...")


def _generate_fallback_recommendations(
    top_results: List[QuizAnswer],
    products_by_supp: Dict[str, List[Dict[str, Any]]] = None
) -> List[QuizRecommendationItem]:
    """生成回退推荐（当 Grok 调用失败时使用）- 根据 supplement_id 匹配商品"""
    print("=" * 40)
    print("USING FALLBACK RECOMMENDATIONS (NOT AI)")
    print("=" * 40)
    items = []
    for i, result in enumerate(top_results, 1):
        # 根据分数计算信心度
        confidence = min(95, 60 + result.total_score * 5)
        
        # 获取该补充品类别下的商品
        recommended_products = []
        if products_by_supp and result.supplement_id in products_by_supp:
            print(f"  Fallback: Adding products for {result.supplement_id}")
            for idx, p in enumerate(products_by_supp[result.supplement_id][:2], 1):  # 最多2个
                # 生成更好的默认推荐理由
                why_reasons = [
                    f"此商品屬於您需要補充的「{result.group}」類別",
                    "已通過平台審核，品質有保障"
                ]
                
                # 根据商品信息添加更多理由
                if p.get('price') and p['price'] < 500:
                    why_reasons.append("價格實惠，適合日常補充")
                elif p.get('price') and p['price'] >= 500:
                    why_reasons.append("高品質配方，值得投資")
                
                if p.get('partner_name'):
                    why_reasons.append(f"來自信賴品牌：{p['partner_name']}")
                
                recommended_products.append(ProductRecommendation(
                    product_id=p['id'],
                    product_name=p['name'],
                    why_this_product=why_reasons[:3],  # 最多3条
                    price=p.get('price'),
                    currency=p.get('currency', 'TWD'),
                    purchase_url=p['purchase_url'],
                    image_url=p.get('image_url'),
                    partner_name=p.get('partner_name'),
                ))
                print(f"    ✓ Added fallback product {idx}: {p['name']}")
        
        items.append(QuizRecommendationItem(
            rank=i,
            supplement_id=result.supplement_id,
            name=result.supplement_name,
            group=result.group,
            why=[
                f"根據問卷評估，您在「{result.group}」方面有較高的補充需求",
                f"問卷分數：{result.total_score} 分",
            ],
            safety=[],
            confidence=confidence,
            recommended_products=recommended_products,
        ))
    
    return items


@router.post("/submit", response_model=QuizRecommendationResponse)
@rate_limit(max_requests=5, window=60)  # 每分钟最多 5 次问卷提交
async def submit_quiz(
    request: Request, 
    quiz_request: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> QuizRecommendationResponse:
    """
    提交问卷答案并获取 Grok 生成的个性化推荐
    
    限制：
    - 每分钟最多 5 次提交（防止短时间内大量请求）
    - 每天最多 4 次 AI 分析（防止滥用 AI API）
    
    - **answers**: 所有补充品的问卷答案（30个）
    - **top_results**: 前端预筛选的结果（仅作参考，AI 会自己决定推荐）
    
    返回 AI 生成的个性化营养推荐，包含：
    - AI 自主选择的 3 个最适合的补充品
    - 推荐原因（3-5 条）
    - 信心分数（0-100）
    - 免责声明
    """
    print("=" * 80)
    print("QUIZ SUBMISSION RECEIVED")
    print("=" * 80)
    
    # 优先使用 X-User-ID 请求头进行用户标识，否则回退到 IP 地址
    user_identifier = request.headers.get("X-User-ID")
    if not user_identifier:
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        user_identifier = client_ip
        print(f"Using client IP for tracking: {user_identifier}")
    else:
        print(f"Using User ID for tracking: {user_identifier}")
    
    # 检查每日使用限制
    try:
        usage_info = await usage_tracker.check_and_increment(db, user_identifier)
        print(f"✓ Daily usage check passed. Remaining: {usage_info['remaining']}")
    except HTTPException as e:
        print(f"✗ Daily usage limit exceeded for user: {user_identifier}")
        raise
    
    session_id = str(uuid4())
    all_answers = quiz_request.answers  # 使用所有答案，不只是 top_results
    health_data = quiz_request.health_data  # 获取体检报告数据
    
    print(f"Total answers count: {len(all_answers)}")
    print(f"Health data provided: {bool(health_data)}")
    
    # 转换健康数据为 lab_metrics 格式
    lab_metrics = None
    if health_data:
        try:
            lab_metrics = convert_health_data_to_lab_metrics(health_data)
            print(f"✓ Converted health data to {len(lab_metrics)} lab metrics")
            for metric in lab_metrics:
                if metric['flag'] != 'normal':
                    print(f"  - {metric['name_zh']}: {metric['value']} {metric['unit']} ({metric['flag']})")
        except Exception as e:
            print(f"✗ Failed to convert health data: {e}")
            lab_metrics = None
    
    # 优先从数据库系统配置获取 Grok API Key，方便通过管理后台切换，
    # 若数据库没有配置则回退到环境变量
    db_config_result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "GROK_API_KEY")
    )
    db_config = db_config_result.scalar_one_or_none()
    api_key = (db_config.value if db_config and db_config.value else None) or settings.grok_api_key
    print(f"Grok API Key source: {'DB' if db_config and db_config.value else 'ENV'}")
    print(f"Grok API Key configured: {bool(api_key)}")
    if api_key:
        print(f"API Key length: {len(api_key)}")
    
    logger.info(f"Quiz submission received with {len(all_answers)} answers")
    
    if not all_answers:
        return QuizRecommendationResponse(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            items=[],
            disclaimer=DISCLAIMER_ZH,
            ai_generated=False,
        )
    
    # 尝试使用 Grok 生成推荐
    items = []
    ai_generated = False
    
    # 获取所有已审核的商品
    products_by_supp = await get_all_approved_products()
    print(f"Loaded products for {len(products_by_supp)} supplement categories")
    
    if api_key:
        try:
            from openai import OpenAI
            
            print("=" * 80)
            print("ATTEMPTING GROK API CALL - AI WILL DECIDE RECOMMENDATIONS AND PRODUCTS")
            print("=" * 80)
            logger.info(f"Using xAI Grok API for quiz recommendations")
            
            # 使用信号量控制并发 - 等待获取锁
            async with _grok_semaphore:
                print("✓ Acquired Grok API semaphore lock")
                logger.info("Acquired Grok API semaphore lock")
                
                # 初始化 xAI Grok Client
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1"
                )
                
                print("✓ Initialized xAI Grok client")
                
                # 构建 Prompt - 发送所有答案、商品和体检报告数据
                prompt = _build_quiz_prompt(all_answers, products_by_supp, lab_metrics)
                
                # 打印使用的 prompt 类型
                if lab_metrics:
                    print(f"✓ Using PROMPT_WITH_LAB - lab_metrics has {len(lab_metrics)} items")
                    for m in lab_metrics[:3]:
                        print(f"  - {m['name_zh']}: {m['value']} {m['unit']} ({m['flag']})")
                else:
                    print("✓ Using PROMPT_NO_LAB - no lab data provided")
                
                # 调用 Grok API
                print("Calling Grok API with ALL answers and products...")
                logger.info(f"Prompt length: {len(prompt)} characters")
                
                import httpx
                # 增加超时时间到 120 秒，并添加重试机制
                max_retries = 2
                retry_count = 0
                last_error = None
                
                while retry_count <= max_retries:
                    try:
                        print(f"Attempt {retry_count + 1}/{max_retries + 1}...")
                        response = client.chat.completions.create(
                            model="grok-4-1-fast-reasoning",  # fast-reasoning 模型（已验证可用）
                            messages=[
                                {"role": "system", "content": "You are a professional nutritionist. Return ONLY valid JSON."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7,  # 提高到 0.7 增加推荐多样性
                            max_tokens=4096,
                            timeout=180.0,  # 完整模型需要更长超时
                            response_format={"type": "json_object"}  # Grok 支持 json_object
                        )
                        print("✓ xAI Grok API call successful")
                        logger.info("xAI Grok API call successful")
                        break  # 成功则跳出循环
                    except Exception as retry_error:
                        last_error = retry_error
                        retry_count += 1
                        if retry_count <= max_retries:
                            wait_time = retry_count * 2  # 递增等待时间
                            print(f"✗ Attempt failed, waiting {wait_time}s before retry...")
                            logger.warning(f"Grok API attempt {retry_count} failed: {retry_error}")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"✗ All {max_retries + 1} attempts failed")
                            raise last_error
                
                # 解析响应
                response_text = response.choices[0].message.content or ""
                print(f"Grok response length: {len(response_text)}")
                print(f"Grok response: {response_text[:500]}")
                
                if not response_text.strip():
                    raise ValueError("Grok returned empty response")
                
                logger.info(f"Grok response preview: {response_text[:500]}")
                raw_recommendations = _parse_ai_response(response_text)
                print(f"✓ Parsed {len(raw_recommendations)} recommendations from Grok")
            
            # 信号量释放后继续处理结果
            # 构建推荐项 - AI 选择的补充品和商品
            print(f"Building recommendations from AI choices...")
            
            # 创建 ID 到答案的映射
            answer_map = {a.supplement_id: a for a in all_answers}
            
            # 创建商品 ID 到商品的映射（用于快速查找）
            all_products_map = {}
            for supp_id, products in products_by_supp.items():
                for p in products:
                    all_products_map[p['id']] = p
            
            for i, raw_rec in enumerate(raw_recommendations):
                print(f"  Raw rec {i}: {raw_rec}")
                supplement_id = raw_rec.get("supplement_id", "")
                print(f"    AI chose supplement_id: {supplement_id}")
                
                # 从所有答案中找到对应的补充品
                original = answer_map.get(supplement_id)
                
                if not original:
                    print(f"    ✗ No matching supplement found for ID: {supplement_id}")
                    # 尝试模糊匹配
                    for aid, ans in answer_map.items():
                        if supplement_id.lower() in aid.lower() or aid.lower() in supplement_id.lower():
                            original = ans
                            print(f"    ✓ Fuzzy matched to: {aid}")
                            break
                
                if not original:
                    print(f"    ✗ Skipping - no match found")
                    continue
                
                print(f"    ✓ Found matching supplement: {original.supplement_name}")
                why = raw_rec.get("why", [])
                if len(why) < 3:
                    why.extend([
                        f"根據 AI 分析，{original.supplement_name}是您目前最需要關注的營養補充方向",
                        f"您在{original.group}相關問題的回答顯示有補充需求",
                    ][:3 - len(why)])
                
                # 处理 AI 推荐的商品
                recommended_products = []
                raw_products = raw_rec.get("recommended_products", [])
                print(f"    AI recommended {len(raw_products)} products: {raw_products}")
                
                for raw_prod in raw_products:
                    product_id = raw_prod.get("product_id", "")
                    print(f"      Looking for product_id: {product_id}")
                    product_info = all_products_map.get(product_id)
                    
                    if product_info:
                        recommended_products.append(ProductRecommendation(
                            product_id=product_id,
                            product_name=product_info['name'],
                            why_this_product=raw_prod.get("why_this_product", ["AI 推薦此商品"]),
                            price=product_info.get('price'),
                            currency=product_info.get('currency', 'TWD'),
                            purchase_url=product_info['purchase_url'],
                            image_url=product_info.get('image_url'),
                            partner_name=product_info.get('partner_name'),
                        ))
                        print(f"      ✓ Added product: {product_info['name']}")
                    else:
                        print(f"      ✗ Product not found by ID: {product_id}")
                        print(f"      Available product IDs: {list(all_products_map.keys())}")
                
                # 如果没有匹配到商品，用 supplement_id 匹配该类别下的商品
                if not recommended_products and original.supplement_id in products_by_supp:
                    print(f"    → No products matched, trying supplement_id: {original.supplement_id}")
                    supp_products = products_by_supp[original.supplement_id]
                    print(f"    → Found {len(supp_products)} products for this supplement")
                    for p in supp_products[:2]:
                        # 如果 AI 给了推荐理由就用，否则用默认理由
                        why_reasons = ["AI 推薦此商品", "符合您的營養需求"]
                        if raw_products and raw_products[0].get("why_this_product"):
                            why_reasons = raw_products[0].get("why_this_product")
                        recommended_products.append(ProductRecommendation(
                            product_id=p['id'],
                            product_name=p['name'],
                            why_this_product=why_reasons,
                            price=p.get('price'),
                            currency=p.get('currency', 'TWD'),
                            purchase_url=p['purchase_url'],
                            image_url=p.get('image_url'),
                            partner_name=p.get('partner_name'),
                        ))
                        print(f"      ✓ Matched by supplement_id: {p['name']}")
                
                items.append(QuizRecommendationItem(
                    rank=raw_rec.get("rank", len(items) + 1),
                    supplement_id=original.supplement_id,
                    name=original.supplement_name,
                    group=original.group,
                    why=why[:5],
                    safety=raw_rec.get("safety", []),
                    confidence=max(0, min(100, raw_rec.get("confidence", 70))),
                    recommended_products=recommended_products,
                ))
                print(f"    ✓ Added AI recommendation with {len(recommended_products)} products")
            
            print(f"✓ Built {len(items)} AI-chosen recommendations")
            ai_generated = len(items) > 0
            logger.info(f"Grok generated {len(items)} recommendations")
            
        except Exception as e:
            print(f"❌ Grok API Error: {str(e)}")
            logger.error(f"Grok API failed: {e}")
            import traceback
            traceback.print_exc()
            
            # 根据错误类型返回不同的错误信息
            error_message = str(e)
            error_type = type(e).__name__
            
            if "429" in error_message or "并发" in error_message or "limit" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="AI 分析服務繁忙，請稍後再試。API 並發限制已達上限。"
                )
            elif "timeout" in error_message.lower() or "APITimeoutError" in error_type:
                # 超时错误 - 提供更友好的提示
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="AI 分析處理時間較長，請稍後重試。建議：1) 等待 1-2 分鐘後重試 2) 檢查網絡連接 3) 如持續失敗請聯繫客服"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"AI 分析服務暫時不可用，請稍後再試。錯誤：{error_type}"
                )
    
    # 如果没有 API key，返回错误
    if not items:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 分析服务未配置，请联系管理员。"
        )
    
    # 确保排名正确
    items.sort(key=lambda x: x.rank)
    for i, item in enumerate(items, 1):
        item.rank = i
    
    # 构建响应
    response = QuizRecommendationResponse(
        session_id=session_id,
        generated_at=datetime.utcnow(),
        items=items,
        disclaimer=DISCLAIMER_ZH,
        ai_generated=ai_generated,
        based_on_lab_report=bool(lab_metrics),  # 标记是否基于体检报告
    )
    
    # 如果用户已登录，保存历史记录
    if current_user:
        try:
            # 准备要保存的数据
            answers_data = [a.dict() for a in all_answers]
            health_data = quiz_request.health_data
            recommendations_data = response.dict()
            
            # 【静态加密】加密敏感的健康数据
            # 将 JSON 数据转换为字符串后加密
            encrypted_answers = encryption_service.encrypt(json.dumps(answers_data))
            encrypted_health_data = encryption_service.encrypt(
                json.dumps(health_data) if health_data else ""
            ) if health_data else None
            encrypted_recommendations = encryption_service.encrypt(json.dumps(recommendations_data))
            
            logger.info(f"Encrypting quiz history for user {current_user.id}")
            
            # 注意：这里我们将加密后的字符串存储在 JSON 字段中
            # 实际生产环境应该添加专门的加密字段，或使用数据库级加密
            history = QuizHistory(
                user_id=current_user.id,
                session_id=session_id,
                answers={"encrypted": encrypted_answers},  # 存储加密数据
                health_data={"encrypted": encrypted_health_data} if encrypted_health_data else None,
                recommendations={"encrypted": encrypted_recommendations},
                ai_generated=ai_generated
            )
            db.add(history)
            await db.commit()
            logger.info(f"✓ Saved encrypted quiz history for user {current_user.id}")
        except Exception as e:
            logger.error(f"✗ Failed to save quiz history: {e}")
            # 不影响主流程，继续返回结果
    
    return response
