"""混合评分引擎 - 实现问卷分数 + 报告分数的加权计算

算法流程：
1. 问卷评分：根据用户答案计算每个营养素的分数（0-100）
2. 报告评分：从 AI 提取的健康数据计算每个营养素的分数（0-100）
3. 混合评分：报告分数 * 0.7 + 问卷分数 * 0.3
4. 排序并返回 top 5
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class NutrientScore:
    """营养素分数"""
    nutrient: str
    questionnaire_score: float  # 问卷分数 (0-100)
    report_score: float         # 报告分数 (0-100)
    final_score: float          # 最终分数 (0-100)
    reasons: List[str]          # 评分原因


class QuestionnaireScorer:
    """问卷评分器 - 根据用户答案计算营养素分数"""
    
    # 健康目标与营养素的匹配关系（每个目标对应的营养素及其权重）
    GOAL_NUTRIENT_MAPPING = {
        "weight_loss": {
            "probiotics": 25,
            "protein_powder": 30,
            "vitamin_b_complex": 20,
            "green_tea_extract": 25,
        },
        "muscle_gain": {
            "protein_powder": 35,
            "vitamin_b_complex": 20,
            "magnesium": 20,
            "calcium": 15,
            "zinc": 10,
        },
        "energy": {
            "vitamin_b_complex": 30,
            "iron": 25,
            "coq10": 20,
            "vitamin_d": 15,
            "magnesium": 10,
        },
        "immunity": {
            "vitamin_c": 25,
            "vitamin_d": 25,
            "zinc": 20,
            "probiotics": 20,
            "omega_3": 10,
        },
        "skin_health": {
            "collagen": 30,
            "vitamin_c": 25,
            "vitamin_e": 20,
            "zinc": 15,
            "omega_3": 10,
        },
        "bone_health": {
            "calcium": 30,
            "vitamin_d": 30,
            "magnesium": 20,
            "vitamin_k": 20,
        },
        "heart_health": {
            "omega_3": 35,
            "coq10": 25,
            "magnesium": 20,
            "vitamin_d": 20,
        },
        "brain_health": {
            "omega_3": 30,
            "vitamin_b_complex": 25,
            "vitamin_d": 20,
            "magnesium": 15,
            "ginkgo": 10,
        },
        "sleep": {
            "magnesium": 35,
            "melatonin": 30,
            "vitamin_d": 20,
            "calcium": 15,
        },
    }
    
    # 饮食偏好对营养素的影响（加分或减分）
    DIETARY_PREFERENCE_MODIFIERS = {
        "vegetarian": {
            "iron": 15,
            "vitamin_b12": 15,
            "zinc": 10,
            "omega_3": 10,  # 植物性 omega-3
        },
        "vegan": {
            "vitamin_b12": 20,
            "iron": 15,
            "calcium": 15,
            "vitamin_d": 15,
            "zinc": 10,
            "omega_3": 10,
        },
        "keto": {
            "magnesium": 15,
            "sodium": 10,
            "potassium": 10,
            "vitamin_b_complex": 10,
        },
        "paleo": {
            "vitamin_d": 10,
            "omega_3": 10,
            "magnesium": 10,
        },
    }
    
    def calculate_scores(
        self,
        goals: List[str],
        dietary_preferences: List[str],
        budget_max: Optional[float] = None,
    ) -> Dict[str, NutrientScore]:
        """
        根据问卷答案计算营养素分数
        
        Args:
            goals: 健康目标列表
            dietary_preferences: 饮食偏好列表
            budget_max: 预算上限
            
        Returns:
            Dict[str, NutrientScore]: 营养素分数字典
        """
        # 初始化所有营养素的分数为 0
        nutrient_scores: Dict[str, float] = {}
        nutrient_reasons: Dict[str, List[str]] = {}
        
        # 1. 根据健康目标计算基础分数
        for goal in goals:
            if goal in self.GOAL_NUTRIENT_MAPPING:
                for nutrient, score in self.GOAL_NUTRIENT_MAPPING[goal].items():
                    nutrient_scores[nutrient] = nutrient_scores.get(nutrient, 0) + score
                    if nutrient not in nutrient_reasons:
                        nutrient_reasons[nutrient] = []
                    nutrient_reasons[nutrient].append(f"符合您的健康目标：{goal}")
        
        # 2. 根据饮食偏好调整分数
        for preference in dietary_preferences:
            if preference == "no_preference":
                continue
            if preference in self.DIETARY_PREFERENCE_MODIFIERS:
                for nutrient, modifier in self.DIETARY_PREFERENCE_MODIFIERS[preference].items():
                    nutrient_scores[nutrient] = nutrient_scores.get(nutrient, 0) + modifier
                    if nutrient not in nutrient_reasons:
                        nutrient_reasons[nutrient] = []
                    nutrient_reasons[nutrient].append(f"适合您的饮食偏好：{preference}")
        
        # 3. 归一化分数到 0-100
        if nutrient_scores:
            max_score = max(nutrient_scores.values())
            if max_score > 0:
                for nutrient in nutrient_scores:
                    nutrient_scores[nutrient] = min(100, (nutrient_scores[nutrient] / max_score) * 100)
        
        # 4. 构建 NutrientScore 对象
        result = {}
        for nutrient, score in nutrient_scores.items():
            result[nutrient] = NutrientScore(
                nutrient=nutrient,
                questionnaire_score=score,
                report_score=0.0,  # 稍后由报告评分器填充
                final_score=score,  # 如果没有报告，就用问卷分数
                reasons=nutrient_reasons.get(nutrient, [])
            )
        
        return result


class ReportScorer:
    """报告评分器 - 根据健康指标计算营养素分数"""
    
    # 健康指标与营养素的关系（指标异常时推荐的营养素及其权重）
    METRIC_NUTRIENT_MAPPING = {
        # 血液指标
        "hemoglobin": {
            "low": {"iron": 35, "vitamin_b12": 25, "folic_acid": 20, "vitamin_c": 10},
            "high": {},
        },
        "ferritin": {
            "low": {"iron": 40, "vitamin_c": 15},
            "high": {},
        },
        "vitamin_d": {
            "low": {"vitamin_d": 50},
            "high": {},
        },
        "vitamin_b12": {
            "low": {"vitamin_b12": 50, "folic_acid": 15},
            "high": {},
        },
        "folic_acid": {
            "low": {"folic_acid": 50, "vitamin_b12": 15},
            "high": {},
        },
        
        # 血糖相关
        "fasting_glucose": {
            "low": {"chromium": 20, "vitamin_b_complex": 15},
            "high": {"chromium": 25, "magnesium": 20, "vitamin_d": 15, "omega_3": 15},
        },
        "hba1c": {
            "low": {},
            "high": {"chromium": 25, "magnesium": 20, "vitamin_d": 15, "omega_3": 15},
        },
        
        # 血脂
        "total_cholesterol": {
            "low": {},
            "high": {"omega_3": 30, "coq10": 20, "niacin": 15, "fiber": 15},
        },
        "ldl": {
            "low": {},
            "high": {"omega_3": 35, "coq10": 20, "niacin": 15},
        },
        "hdl": {
            "low": {"omega_3": 30, "niacin": 20, "vitamin_d": 15},
            "high": {},
        },
        "triglycerides": {
            "low": {},
            "high": {"omega_3": 40, "niacin": 20, "fiber": 15},
        },
        
        # 肝功能
        "alt": {
            "low": {},
            "high": {"milk_thistle": 30, "vitamin_e": 20, "omega_3": 15},
        },
        "ast": {
            "low": {},
            "high": {"milk_thistle": 30, "vitamin_e": 20, "omega_3": 15},
        },
        
        # 肾功能
        "creatinine": {
            "low": {},
            "high": {"omega_3": 20, "coq10": 15},
        },
        "uric_acid": {
            "low": {},
            "high": {"vitamin_c": 25, "cherry_extract": 20, "quercetin": 15},
        },
        
        # 甲状腺
        "tsh": {
            "low": {"selenium": 20, "zinc": 15},
            "high": {"selenium": 25, "zinc": 20, "vitamin_d": 15, "iodine": 15},
        },
    }
    
    # 参考范围（用于判断高低）
    REFERENCE_RANGES = {
        "hemoglobin": {"low": 12.0, "high": 17.0, "unit": "g/dL"},
        "ferritin": {"low": 30, "high": 300, "unit": "ng/mL"},
        "vitamin_d": {"low": 30, "high": 100, "unit": "ng/mL"},
        "vitamin_b12": {"low": 200, "high": 900, "unit": "pg/mL"},
        "folic_acid": {"low": 3, "high": 17, "unit": "ng/mL"},
        "fasting_glucose": {"low": 70, "high": 100, "unit": "mg/dL"},
        "hba1c": {"low": 4.0, "high": 5.7, "unit": "%"},
        "total_cholesterol": {"low": 125, "high": 200, "unit": "mg/dL"},
        "ldl": {"low": 0, "high": 100, "unit": "mg/dL"},
        "hdl": {"low": 40, "high": 200, "unit": "mg/dL"},
        "triglycerides": {"low": 0, "high": 150, "unit": "mg/dL"},
        "alt": {"low": 0, "high": 40, "unit": "U/L"},
        "ast": {"low": 0, "high": 40, "unit": "U/L"},
        "creatinine": {"low": 0.6, "high": 1.2, "unit": "mg/dL"},
        "uric_acid": {"low": 3.5, "high": 7.2, "unit": "mg/dL"},
        "tsh": {"low": 0.4, "high": 4.0, "unit": "mIU/L"},
    }
    
    def calculate_scores(
        self,
        lab_metrics: List[Dict[str, Any]],
    ) -> Dict[str, NutrientScore]:
        """
        根据健康指标计算营养素分数
        
        Args:
            lab_metrics: 健康指标列表，格式：
                [
                    {"name": "hemoglobin", "value": 11.5, "unit": "g/dL", "flag": "low"},
                    ...
                ]
            
        Returns:
            Dict[str, NutrientScore]: 营养素分数字典
        """
        nutrient_scores: Dict[str, float] = {}
        nutrient_reasons: Dict[str, List[str]] = {}
        
        for metric in lab_metrics:
            metric_name = metric.get("name", "").lower()
            value = metric.get("value")
            flag = metric.get("flag", "normal").lower()
            
            if metric_name not in self.METRIC_NUTRIENT_MAPPING:
                continue
            
            # 如果没有 flag，根据参考范围判断
            if flag == "normal" and metric_name in self.REFERENCE_RANGES:
                ref = self.REFERENCE_RANGES[metric_name]
                if value is not None:
                    if value < ref["low"]:
                        flag = "low"
                    elif value > ref["high"]:
                        flag = "high"
            
            # 获取对应的营养素推荐
            if flag in ["low", "high"]:
                mapping = self.METRIC_NUTRIENT_MAPPING[metric_name].get(flag, {})
                for nutrient, score in mapping.items():
                    nutrient_scores[nutrient] = nutrient_scores.get(nutrient, 0) + score
                    if nutrient not in nutrient_reasons:
                        nutrient_reasons[nutrient] = []
                    nutrient_reasons[nutrient].append(
                        f"您的 {metric_name} 指标 {flag}（{value}），建议补充"
                    )
        
        # 归一化分数到 0-100
        if nutrient_scores:
            max_score = max(nutrient_scores.values())
            if max_score > 0:
                for nutrient in nutrient_scores:
                    nutrient_scores[nutrient] = min(100, (nutrient_scores[nutrient] / max_score) * 100)
        
        # 构建 NutrientScore 对象
        result = {}
        for nutrient, score in nutrient_scores.items():
            result[nutrient] = NutrientScore(
                nutrient=nutrient,
                questionnaire_score=0.0,  # 稍后由混合评分器填充
                report_score=score,
                final_score=score,  # 如果没有问卷，就用报告分数
                reasons=nutrient_reasons.get(nutrient, [])
            )
        
        return result


class HybridScoringEngine:
    """混合评分引擎 - 整合问卷分数和报告分数"""
    
    # 权重配置
    REPORT_WEIGHT = 0.7   # 报告分数权重
    QUESTIONNAIRE_WEIGHT = 0.3  # 问卷分数权重
    
    def __init__(self):
        """初始化混合评分引擎"""
        self.questionnaire_scorer = QuestionnaireScorer()
        self.report_scorer = ReportScorer()
    
    def calculate_hybrid_scores(
        self,
        goals: List[str],
        dietary_preferences: List[str],
        lab_metrics: Optional[List[Dict[str, Any]]] = None,
        budget_max: Optional[float] = None,
    ) -> List[NutrientScore]:
        """
        计算混合分数
        
        Args:
            goals: 健康目标列表
            dietary_preferences: 饮食偏好列表
            lab_metrics: 健康指标列表（可选）
            budget_max: 预算上限（可选）
            
        Returns:
            List[NutrientScore]: 按最终分数排序的营养素列表
        """
        # 1. 计算问卷分数
        questionnaire_scores = self.questionnaire_scorer.calculate_scores(
            goals=goals,
            dietary_preferences=dietary_preferences,
            budget_max=budget_max,
        )
        
        # 2. 计算报告分数（如果有报告）
        report_scores = {}
        if lab_metrics:
            report_scores = self.report_scorer.calculate_scores(lab_metrics)
        
        # 3. 合并分数
        all_nutrients = set(questionnaire_scores.keys()) | set(report_scores.keys())
        hybrid_scores: Dict[str, NutrientScore] = {}
        
        for nutrient in all_nutrients:
            q_score_obj = questionnaire_scores.get(nutrient)
            r_score_obj = report_scores.get(nutrient)
            
            # 获取分数
            q_score = q_score_obj.questionnaire_score if q_score_obj else 0.0
            r_score = r_score_obj.report_score if r_score_obj else 0.0
            
            # 计算最终分数
            if lab_metrics:
                # 有报告：使用加权平均
                final_score = (r_score * self.REPORT_WEIGHT + 
                             q_score * self.QUESTIONNAIRE_WEIGHT)
            else:
                # 没有报告：只用问卷分数
                final_score = q_score
            
            # 合并原因
            reasons = []
            if q_score_obj:
                reasons.extend(q_score_obj.reasons)
            if r_score_obj:
                reasons.extend(r_score_obj.reasons)
            
            hybrid_scores[nutrient] = NutrientScore(
                nutrient=nutrient,
                questionnaire_score=q_score,
                report_score=r_score,
                final_score=final_score,
                reasons=reasons,
            )
        
        # 4. 按最终分数排序
        sorted_scores = sorted(
            hybrid_scores.values(),
            key=lambda x: x.final_score,
            reverse=True
        )
        
        logger.info(f"Calculated hybrid scores for {len(sorted_scores)} nutrients")
        if sorted_scores:
            logger.info(f"Top 5: {[(s.nutrient, round(s.final_score, 2)) for s in sorted_scores[:5]]}")
        
        return sorted_scores
    
    def get_top_n(
        self,
        goals: List[str],
        dietary_preferences: List[str],
        lab_metrics: Optional[List[Dict[str, Any]]] = None,
        budget_max: Optional[float] = None,
        n: int = 5,
    ) -> List[NutrientScore]:
        """
        获取 top N 营养素
        
        Args:
            goals: 健康目标列表
            dietary_preferences: 饮食偏好列表
            lab_metrics: 健康指标列表（可选）
            budget_max: 预算上限（可选）
            n: 返回数量（默认 5）
            
        Returns:
            List[NutrientScore]: top N 营养素列表
        """
        all_scores = self.calculate_hybrid_scores(
            goals=goals,
            dietary_preferences=dietary_preferences,
            lab_metrics=lab_metrics,
            budget_max=budget_max,
        )
        
        return all_scores[:n]


# 全局实例
hybrid_scoring_engine = HybridScoringEngine()
