"""规则引擎服务 - 安全护栏规则定义与匹配逻辑

实现需求 4.2, 4.3, 4.4:
- 对过敏、慢病和用药交互应用安全约束
- 若推荐与用户过敏冲突，则阻挡或大幅降权该推荐
- 若推荐有用药交互风险，则添加安全警告并要求显示专业咨询提示
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class RuleAction(str, Enum):
    """规则动作类型"""
    ALLOW = "allow"      # 允许推荐
    WARN = "warn"        # 添加警告但允许
    BLOCK = "block"      # 阻挡推荐


class Severity(str, Enum):
    """严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __lt__(self, other):
        """比较严重程度（用于排序）"""
        if not isinstance(other, Severity):
            return NotImplemented
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) < order.index(other)
    
    def __le__(self, other):
        if not isinstance(other, Severity):
            return NotImplemented
        return self == other or self < other
    
    def __gt__(self, other):
        if not isinstance(other, Severity):
            return NotImplemented
        return not self <= other
    
    def __ge__(self, other):
        if not isinstance(other, Severity):
            return NotImplemented
        return not self < other


@dataclass
class DrugInteraction:
    """用药交互定义"""
    drug: str                    # 药物名称/类别
    nutrient: str                # 营养素
    severity: Severity           # 严重程度
    description: str             # 交互描述
    description_zh: str          # 中文描述


@dataclass
class AllergyRule:
    """过敏规则定义"""
    allergen: str                # 过敏原
    blocked_nutrients: List[str] # 需要阻挡的营养素
    warning_nutrients: List[str] # 需要警告的营养素
    description: str             # 规则描述
    description_zh: str          # 中文描述


@dataclass
class ChronicConditionRule:
    """慢病规则定义"""
    condition: str               # 慢病名称
    blocked_nutrients: List[str] # 需要阻挡的营养素
    warning_nutrients: List[str] # 需要警告的营养素
    recommended_nutrients: List[str]  # 推荐的营养素
    description: str             # 规则描述
    description_zh: str          # 中文描述


@dataclass
class SafetyInfo:
    """安全信息"""
    warnings: List[str] = field(default_factory=list)
    requires_professional_consult: bool = False
    interactions: List[DrugInteraction] = field(default_factory=list)


@dataclass
class RuleResult:
    """规则匹配结果"""
    nutrient: str
    action: RuleAction
    reason: Optional[str] = None
    reason_zh: Optional[str] = None
    weight_modifier: float = 1.0  # 权重调整系数 (0-1)
    safety_info: SafetyInfo = field(default_factory=SafetyInfo)


@dataclass
class SafetyCheck:
    """安全检查结果"""
    safe: bool
    warnings: List[str] = field(default_factory=list)
    blocked_by: Optional[str] = None


@dataclass
class NutrientCandidate:
    """营养素候选"""
    nutrient: str
    base_score: float


@dataclass
class HealthProfile:
    """健康档案（用于规则引擎）"""
    allergies: List[str] = field(default_factory=list)
    chronic_conditions: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    dietary_preferences: List[str] = field(default_factory=list)
    lab_metrics: Optional[Dict] = None


# ============================================================================
# 安全规则数据定义 (任务 8.1)
# ============================================================================

# 过敏规则库
ALLERGY_RULES: Dict[str, AllergyRule] = {
    "shellfish": AllergyRule(
        allergen="shellfish",
        blocked_nutrients=["glucosamine", "chitosan", "omega_3_krill"],
        warning_nutrients=["omega_3"],
        description="Shellfish allergy may react to shellfish-derived supplements",
        description_zh="贝类过敏可能对贝类来源的补充剂产生反应"
    ),
    "nuts": AllergyRule(
        allergen="nuts",
        blocked_nutrients=["almond_protein", "walnut_oil"],
        warning_nutrients=["vitamin_e"],  # 部分维生素E来源于坚果
        description="Nut allergy may react to nut-derived supplements",
        description_zh="坚果过敏可能对坚果来源的补充剂产生反应"
    ),
    "dairy": AllergyRule(
        allergen="dairy",
        blocked_nutrients=["whey_protein", "casein", "lactoferrin"],
        warning_nutrients=["calcium", "vitamin_d"],  # 部分来源于乳制品
        description="Dairy allergy may react to dairy-derived supplements",
        description_zh="乳制品过敏可能对乳制品来源的补充剂产生反应"
    ),
    "gluten": AllergyRule(
        allergen="gluten",
        blocked_nutrients=["wheat_germ_oil", "barley_grass"],
        warning_nutrients=["b_vitamins"],  # 部分B族维生素可能含麸质
        description="Gluten sensitivity may react to gluten-containing supplements",
        description_zh="麸质敏感可能对含麸质的补充剂产生反应"
    ),
    "soy": AllergyRule(
        allergen="soy",
        blocked_nutrients=["soy_protein", "soy_lecithin", "soy_isoflavones"],
        warning_nutrients=["vitamin_e"],  # 部分维生素E来源于大豆
        description="Soy allergy may react to soy-derived supplements",
        description_zh="大豆过敏可能对大豆来源的补充剂产生反应"
    ),
    "fish": AllergyRule(
        allergen="fish",
        blocked_nutrients=["fish_oil", "omega_3_fish", "cod_liver_oil"],
        warning_nutrients=["omega_3"],
        description="Fish allergy may react to fish-derived supplements",
        description_zh="鱼类过敏可能对鱼类来源的补充剂产生反应"
    ),
}

# 慢病规则库
CHRONIC_CONDITION_RULES: Dict[str, ChronicConditionRule] = {
    "diabetes": ChronicConditionRule(
        condition="diabetes",
        blocked_nutrients=[],
        warning_nutrients=["chromium", "alpha_lipoic_acid", "cinnamon"],
        recommended_nutrients=["vitamin_d", "magnesium", "omega_3", "b_vitamins"],
        description="Diabetes patients should monitor blood sugar when taking certain supplements",
        description_zh="糖尿病患者服用某些补充剂时应监测血糖"
    ),
    "hypertension": ChronicConditionRule(
        condition="hypertension",
        blocked_nutrients=["licorice"],
        warning_nutrients=["sodium", "caffeine", "ginseng"],
        recommended_nutrients=["magnesium", "potassium", "omega_3", "coq10"],
        description="Hypertension patients should avoid supplements that may raise blood pressure",
        description_zh="高血压患者应避免可能升高血压的补充剂"
    ),
    "heart_disease": ChronicConditionRule(
        condition="heart_disease",
        blocked_nutrients=["ephedra"],
        warning_nutrients=["vitamin_e_high_dose", "calcium_high_dose", "iron"],
        recommended_nutrients=["omega_3", "coq10", "magnesium", "vitamin_d"],
        description="Heart disease patients should consult before taking certain supplements",
        description_zh="心脏病患者服用某些补充剂前应咨询医生"
    ),
    "thyroid": ChronicConditionRule(
        condition="thyroid",
        blocked_nutrients=[],
        warning_nutrients=["iodine", "kelp", "selenium_high_dose"],
        recommended_nutrients=["selenium", "zinc", "vitamin_d"],
        description="Thyroid patients should be cautious with iodine-containing supplements",
        description_zh="甲状腺疾病患者应谨慎使用含碘补充剂"
    ),
    "kidney_disease": ChronicConditionRule(
        condition="kidney_disease",
        blocked_nutrients=["potassium_high_dose", "phosphorus"],
        warning_nutrients=["vitamin_c_high_dose", "calcium", "magnesium"],
        recommended_nutrients=["vitamin_d", "iron", "b_vitamins"],
        description="Kidney disease patients should limit certain minerals",
        description_zh="肾病患者应限制某些矿物质的摄入"
    ),
}

# 用药交互规则库
DRUG_INTERACTIONS: List[DrugInteraction] = [
    # 抗凝血药物交互
    DrugInteraction(
        drug="warfarin",
        nutrient="vitamin_k",
        severity=Severity.HIGH,
        description="Vitamin K can reduce warfarin effectiveness",
        description_zh="维生素K可能降低华法林的效果"
    ),
    DrugInteraction(
        drug="warfarin",
        nutrient="omega_3",
        severity=Severity.MEDIUM,
        description="Omega-3 may increase bleeding risk with warfarin",
        description_zh="Omega-3与华法林同服可能增加出血风险"
    ),
    DrugInteraction(
        drug="warfarin",
        nutrient="vitamin_e",
        severity=Severity.MEDIUM,
        description="High-dose Vitamin E may increase bleeding risk",
        description_zh="高剂量维生素E可能增加出血风险"
    ),
    DrugInteraction(
        drug="aspirin",
        nutrient="omega_3",
        severity=Severity.MEDIUM,
        description="Omega-3 may increase bleeding risk with aspirin",
        description_zh="Omega-3与阿司匹林同服可能增加出血风险"
    ),
    DrugInteraction(
        drug="aspirin",
        nutrient="ginkgo",
        severity=Severity.HIGH,
        description="Ginkgo may significantly increase bleeding risk with aspirin",
        description_zh="银杏与阿司匹林同服可能显著增加出血风险"
    ),
    # 降压药交互
    DrugInteraction(
        drug="ace_inhibitor",
        nutrient="potassium",
        severity=Severity.HIGH,
        description="ACE inhibitors can increase potassium levels",
        description_zh="ACE抑制剂可能增加钾水平，补钾需谨慎"
    ),
    DrugInteraction(
        drug="calcium_channel_blocker",
        nutrient="grapefruit",
        severity=Severity.HIGH,
        description="Grapefruit can increase drug concentration",
        description_zh="葡萄柚可能增加药物浓度"
    ),
    # 降糖药交互
    DrugInteraction(
        drug="metformin",
        nutrient="vitamin_b12",
        severity=Severity.LOW,
        description="Metformin may reduce B12 absorption, supplementation may be beneficial",
        description_zh="二甲双胍可能降低B12吸收，补充可能有益"
    ),
    DrugInteraction(
        drug="insulin",
        nutrient="chromium",
        severity=Severity.MEDIUM,
        description="Chromium may affect blood sugar, monitor closely",
        description_zh="铬可能影响血糖，需密切监测"
    ),
    # 甲状腺药物交互
    DrugInteraction(
        drug="levothyroxine",
        nutrient="calcium",
        severity=Severity.MEDIUM,
        description="Calcium may reduce levothyroxine absorption, take separately",
        description_zh="钙可能降低左甲状腺素吸收，需分开服用"
    ),
    DrugInteraction(
        drug="levothyroxine",
        nutrient="iron",
        severity=Severity.MEDIUM,
        description="Iron may reduce levothyroxine absorption, take separately",
        description_zh="铁可能降低左甲状腺素吸收，需分开服用"
    ),
    # 抗生素交互
    DrugInteraction(
        drug="tetracycline",
        nutrient="calcium",
        severity=Severity.HIGH,
        description="Calcium significantly reduces tetracycline absorption",
        description_zh="钙显著降低四环素吸收"
    ),
    DrugInteraction(
        drug="fluoroquinolone",
        nutrient="magnesium",
        severity=Severity.HIGH,
        description="Magnesium reduces fluoroquinolone absorption",
        description_zh="镁降低氟喹诺酮类抗生素吸收"
    ),
    # 他汀类药物交互
    DrugInteraction(
        drug="statin",
        nutrient="coq10",
        severity=Severity.LOW,
        description="Statins may reduce CoQ10 levels, supplementation may be beneficial",
        description_zh="他汀类药物可能降低辅酶Q10水平，补充可能有益"
    ),
    DrugInteraction(
        drug="statin",
        nutrient="red_yeast_rice",
        severity=Severity.HIGH,
        description="Red yeast rice contains natural statins, may cause overdose",
        description_zh="红曲米含有天然他汀，可能导致过量"
    ),
]

# 药物名称别名映射（用于匹配用户输入）
DRUG_ALIASES: Dict[str, List[str]] = {
    "warfarin": ["华法林", "warfarin", "coumadin", "香豆素"],
    "aspirin": ["阿司匹林", "aspirin", "拜阿司匹灵"],
    "ace_inhibitor": ["普利类", "依那普利", "卡托普利", "赖诺普利", "enalapril", "captopril", "lisinopril"],
    "calcium_channel_blocker": ["地平类", "氨氯地平", "硝苯地平", "amlodipine", "nifedipine"],
    "metformin": ["二甲双胍", "metformin", "格华止"],
    "insulin": ["胰岛素", "insulin"],
    "levothyroxine": ["左甲状腺素", "优甲乐", "levothyroxine", "synthroid"],
    "tetracycline": ["四环素", "tetracycline", "多西环素", "doxycycline"],
    "fluoroquinolone": ["氟喹诺酮", "左氧氟沙星", "莫西沙星", "levofloxacin", "moxifloxacin"],
    "statin": ["他汀", "阿托伐他汀", "瑞舒伐他汀", "辛伐他汀", "atorvastatin", "rosuvastatin", "simvastatin"],
}


# ============================================================================
# 规则引擎实现 (任务 8.2)
# ============================================================================

class RuleEngine:
    """
    规则引擎 - 安全护栏
    
    实现需求：
    - 4.2: 对过敏、慢病和用药交互应用安全约束
    - 4.3: 若推荐与用户过敏冲突，则阻挡或大幅降权该推荐
    - 4.4: 若推荐有用药交互风险，则添加安全警告并要求显示专业咨询提示
    """
    
    def __init__(self):
        """初始化规则引擎"""
        self.allergy_rules = ALLERGY_RULES
        self.chronic_condition_rules = CHRONIC_CONDITION_RULES
        self.drug_interactions = DRUG_INTERACTIONS
        self.drug_aliases = DRUG_ALIASES
    
    def _normalize_drug_name(self, medication: str) -> Set[str]:
        """
        将用户输入的药物名称标准化为规则库中的药物类别
        
        Args:
            medication: 用户输入的药物名称
            
        Returns:
            匹配的药物类别集合
        """
        medication_lower = medication.lower().strip()
        matched_drugs = set()
        
        # 首先检查是否直接匹配药物键名
        if medication_lower in self.drug_aliases:
            matched_drugs.add(medication_lower)
        
        # 然后检查别名匹配
        for drug_key, aliases in self.drug_aliases.items():
            for alias in aliases:
                if alias.lower() in medication_lower or medication_lower in alias.lower():
                    matched_drugs.add(drug_key)
                    break
        
        return matched_drugs
    
    def _check_allergy_rules(
        self, nutrient: str, allergies: List[str]
    ) -> Optional[RuleResult]:
        """
        检查过敏规则
        
        Args:
            nutrient: 营养素名称
            allergies: 用户过敏列表
            
        Returns:
            RuleResult 如果有匹配的规则，否则 None
        """
        for allergy in allergies:
            allergy_lower = allergy.lower()
            if allergy_lower in self.allergy_rules:
                rule = self.allergy_rules[allergy_lower]
                
                # 检查是否需要阻挡
                if nutrient.lower() in [n.lower() for n in rule.blocked_nutrients]:
                    return RuleResult(
                        nutrient=nutrient,
                        action=RuleAction.BLOCK,
                        reason=f"Blocked due to {allergy} allergy: {rule.description}",
                        reason_zh=f"因{allergy}过敏被阻挡：{rule.description_zh}",
                        weight_modifier=0.0,
                        safety_info=SafetyInfo(
                            warnings=[rule.description_zh],
                            requires_professional_consult=True
                        )
                    )
                
                # 检查是否需要警告
                if nutrient.lower() in [n.lower() for n in rule.warning_nutrients]:
                    return RuleResult(
                        nutrient=nutrient,
                        action=RuleAction.WARN,
                        reason=f"Warning due to {allergy} allergy: {rule.description}",
                        reason_zh=f"因{allergy}过敏需警告：{rule.description_zh}",
                        weight_modifier=0.5,  # 降权 50%
                        safety_info=SafetyInfo(
                            warnings=[rule.description_zh],
                            requires_professional_consult=False
                        )
                    )
        
        return None
    
    def _check_chronic_condition_rules(
        self, nutrient: str, conditions: List[str]
    ) -> Optional[RuleResult]:
        """
        检查慢病规则
        
        Args:
            nutrient: 营养素名称
            conditions: 用户慢病列表
            
        Returns:
            RuleResult 如果有匹配的规则，否则 None
        """
        for condition in conditions:
            condition_lower = condition.lower()
            if condition_lower in self.chronic_condition_rules:
                rule = self.chronic_condition_rules[condition_lower]
                
                # 检查是否需要阻挡
                if nutrient.lower() in [n.lower() for n in rule.blocked_nutrients]:
                    return RuleResult(
                        nutrient=nutrient,
                        action=RuleAction.BLOCK,
                        reason=f"Blocked due to {condition}: {rule.description}",
                        reason_zh=f"因{condition}被阻挡：{rule.description_zh}",
                        weight_modifier=0.0,
                        safety_info=SafetyInfo(
                            warnings=[rule.description_zh],
                            requires_professional_consult=True
                        )
                    )
                
                # 检查是否需要警告
                if nutrient.lower() in [n.lower() for n in rule.warning_nutrients]:
                    return RuleResult(
                        nutrient=nutrient,
                        action=RuleAction.WARN,
                        reason=f"Warning due to {condition}: {rule.description}",
                        reason_zh=f"因{condition}需警告：{rule.description_zh}",
                        weight_modifier=0.7,  # 降权 30%
                        safety_info=SafetyInfo(
                            warnings=[rule.description_zh],
                            requires_professional_consult=True
                        )
                    )
        
        return None
    
    def _check_drug_interactions(
        self, nutrient: str, medications: List[str]
    ) -> Optional[RuleResult]:
        """
        检查用药交互规则
        
        Args:
            nutrient: 营养素名称
            medications: 用户用药列表
            
        Returns:
            RuleResult 如果有匹配的规则，否则 None
        """
        matched_interactions: List[DrugInteraction] = []
        max_severity = Severity.LOW
        
        # 标准化所有用户药物
        normalized_drugs: Set[str] = set()
        for med in medications:
            normalized_drugs.update(self._normalize_drug_name(med))
        
        # 检查每个交互规则
        for interaction in self.drug_interactions:
            if interaction.drug in normalized_drugs:
                if nutrient.lower() == interaction.nutrient.lower():
                    matched_interactions.append(interaction)
                    # 使用自定义比较方法比较严重程度
                    if interaction.severity > max_severity:
                        max_severity = interaction.severity
        
        if not matched_interactions:
            return None
        
        # 根据严重程度决定动作
        warnings = [i.description_zh for i in matched_interactions]
        
        if max_severity == Severity.CRITICAL:
            return RuleResult(
                nutrient=nutrient,
                action=RuleAction.BLOCK,
                reason=f"Blocked due to critical drug interaction",
                reason_zh="因严重用药交互被阻挡",
                weight_modifier=0.0,
                safety_info=SafetyInfo(
                    warnings=warnings,
                    requires_professional_consult=True,
                    interactions=matched_interactions
                )
            )
        elif max_severity == Severity.HIGH:
            return RuleResult(
                nutrient=nutrient,
                action=RuleAction.WARN,
                reason=f"High severity drug interaction warning",
                reason_zh="高风险用药交互警告",
                weight_modifier=0.3,  # 大幅降权 70%
                safety_info=SafetyInfo(
                    warnings=warnings,
                    requires_professional_consult=True,
                    interactions=matched_interactions
                )
            )
        elif max_severity == Severity.MEDIUM:
            return RuleResult(
                nutrient=nutrient,
                action=RuleAction.WARN,
                reason=f"Medium severity drug interaction warning",
                reason_zh="中等风险用药交互警告",
                weight_modifier=0.6,  # 降权 40%
                safety_info=SafetyInfo(
                    warnings=warnings,
                    requires_professional_consult=True,
                    interactions=matched_interactions
                )
            )
        else:  # LOW
            return RuleResult(
                nutrient=nutrient,
                action=RuleAction.ALLOW,
                reason=f"Low severity drug interaction noted",
                reason_zh="低风险用药交互提示",
                weight_modifier=0.9,  # 轻微降权 10%
                safety_info=SafetyInfo(
                    warnings=warnings,
                    requires_professional_consult=False,
                    interactions=matched_interactions
                )
            )
    
    def check_nutrient(self, nutrient: str, profile: HealthProfile) -> SafetyCheck:
        """
        检查单个营养素的安全性
        
        Args:
            nutrient: 营养素名称
            profile: 用户健康档案
            
        Returns:
            SafetyCheck: 安全检查结果
        """
        all_warnings: List[str] = []
        blocked_by: Optional[str] = None
        
        # 检查过敏规则
        allergy_result = self._check_allergy_rules(nutrient, profile.allergies)
        if allergy_result:
            all_warnings.extend(allergy_result.safety_info.warnings)
            if allergy_result.action == RuleAction.BLOCK:
                blocked_by = allergy_result.reason_zh
        
        # 检查慢病规则
        condition_result = self._check_chronic_condition_rules(
            nutrient, profile.chronic_conditions
        )
        if condition_result:
            all_warnings.extend(condition_result.safety_info.warnings)
            if condition_result.action == RuleAction.BLOCK and not blocked_by:
                blocked_by = condition_result.reason_zh
        
        # 检查用药交互
        drug_result = self._check_drug_interactions(nutrient, profile.medications)
        if drug_result:
            all_warnings.extend(drug_result.safety_info.warnings)
            if drug_result.action == RuleAction.BLOCK and not blocked_by:
                blocked_by = drug_result.reason_zh
        
        return SafetyCheck(
            safe=blocked_by is None,
            warnings=all_warnings,
            blocked_by=blocked_by
        )
    
    def apply_safety_rules(
        self, profile: HealthProfile, candidates: List[NutrientCandidate]
    ) -> List[RuleResult]:
        """
        对营养素候选列表应用安全规则
        
        Args:
            profile: 用户健康档案
            candidates: 营养素候选列表
            
        Returns:
            List[RuleResult]: 每个候选的规则结果
        """
        results: List[RuleResult] = []
        
        for candidate in candidates:
            nutrient = candidate.nutrient
            
            # 收集所有规则结果
            allergy_result = self._check_allergy_rules(nutrient, profile.allergies)
            condition_result = self._check_chronic_condition_rules(
                nutrient, profile.chronic_conditions
            )
            drug_result = self._check_drug_interactions(nutrient, profile.medications)
            
            # 合并结果
            merged_result = self._merge_rule_results(
                nutrient, candidate.base_score,
                allergy_result, condition_result, drug_result
            )
            results.append(merged_result)
        
        return results
    
    def _merge_rule_results(
        self,
        nutrient: str,
        base_score: float,
        allergy_result: Optional[RuleResult],
        condition_result: Optional[RuleResult],
        drug_result: Optional[RuleResult]
    ) -> RuleResult:
        """
        合并多个规则结果
        
        Args:
            nutrient: 营养素名称
            base_score: 基础分数
            allergy_result: 过敏规则结果
            condition_result: 慢病规则结果
            drug_result: 用药交互结果
            
        Returns:
            RuleResult: 合并后的结果
        """
        # 收集所有非空结果
        all_results = [r for r in [allergy_result, condition_result, drug_result] if r]
        
        if not all_results:
            # 没有匹配任何规则，允许推荐
            return RuleResult(
                nutrient=nutrient,
                action=RuleAction.ALLOW,
                reason="No safety concerns",
                reason_zh="无安全顾虑",
                weight_modifier=1.0,
                safety_info=SafetyInfo()
            )
        
        # 确定最严格的动作
        final_action = RuleAction.ALLOW
        for result in all_results:
            if result.action == RuleAction.BLOCK:
                final_action = RuleAction.BLOCK
                break
            elif result.action == RuleAction.WARN:
                final_action = RuleAction.WARN
        
        # 计算最终权重修正（取最小值）
        final_weight = min(r.weight_modifier for r in all_results)
        
        # 合并所有警告
        all_warnings: List[str] = []
        all_interactions: List[DrugInteraction] = []
        requires_consult = False
        
        for result in all_results:
            all_warnings.extend(result.safety_info.warnings)
            all_interactions.extend(result.safety_info.interactions)
            if result.safety_info.requires_professional_consult:
                requires_consult = True
        
        # 合并原因
        reasons_zh = [r.reason_zh for r in all_results if r.reason_zh]
        
        return RuleResult(
            nutrient=nutrient,
            action=final_action,
            reason="; ".join([r.reason for r in all_results if r.reason]),
            reason_zh="; ".join(reasons_zh) if reasons_zh else None,
            weight_modifier=final_weight,
            safety_info=SafetyInfo(
                warnings=list(set(all_warnings)),  # 去重
                requires_professional_consult=requires_consult,
                interactions=all_interactions
            )
        )
    
    def get_recommended_nutrients(self, profile: HealthProfile) -> List[str]:
        """
        根据健康档案获取推荐的营养素
        
        Args:
            profile: 用户健康档案
            
        Returns:
            List[str]: 推荐的营养素列表
        """
        recommended: Set[str] = set()
        
        for condition in profile.chronic_conditions:
            condition_lower = condition.lower()
            if condition_lower in self.chronic_condition_rules:
                rule = self.chronic_condition_rules[condition_lower]
                recommended.update(rule.recommended_nutrients)
        
        return list(recommended)
    
    def filter_and_rank_candidates(
        self, profile: HealthProfile, candidates: List[NutrientCandidate]
    ) -> List[NutrientCandidate]:
        """
        过滤并重新排序营养素候选
        
        Args:
            profile: 用户健康档案
            candidates: 营养素候选列表
            
        Returns:
            List[NutrientCandidate]: 过滤和调整权重后的候选列表
        """
        rule_results = self.apply_safety_rules(profile, candidates)
        
        # 过滤掉被阻挡的候选，并调整分数
        filtered_candidates: List[NutrientCandidate] = []
        
        for candidate, result in zip(candidates, rule_results):
            if result.action != RuleAction.BLOCK:
                adjusted_score = candidate.base_score * result.weight_modifier
                filtered_candidates.append(
                    NutrientCandidate(
                        nutrient=candidate.nutrient,
                        base_score=adjusted_score
                    )
                )
        
        # 按调整后的分数排序
        filtered_candidates.sort(key=lambda x: x.base_score, reverse=True)
        
        return filtered_candidates
