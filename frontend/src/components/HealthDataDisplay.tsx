'use client';

import React from 'react';

interface HealthData {
  // 基础信息
  blood_group?: string;

  // 血液指标
  hemoglobin?: number;
  ferritin?: number;
  serum_iron?: number;
  vitamin_d?: number;
  vitamin_b12?: number;
  folic_acid?: number;

  // 血糖相关
  fasting_glucose?: number;
  hba1c?: number;

  // 血脂
  total_cholesterol?: number;
  ldl?: number;
  hdl?: number;
  triglycerides?: number;
  chol_hdl_ratio?: number;

  // 肝功能
  alt?: number;
  ast?: number;
  albumin?: number;
  globulin?: number;
  ag_ratio?: number;
  total_bilirubin?: number;
  direct_bilirubin?: number;
  indirect_bilirubin?: number;
  alkaline_phosphatase?: number;
  gamma_gt?: number;
  total_protein?: number;

  // 肾功能
  creatinine?: number;
  uric_acid?: number;
  urea?: number;
  e_gfr?: number;

  // 骨骼与代谢
  calcium?: number;
  phosphorus?: number;

  // 电解质
  potassium?: number;
  sodium?: number;
  chloride?: number;

  // 甲状腺
  tsh?: number;
  free_t4?: number;

  // 肿瘤标记物
  cea?: number;
  afp?: number;
  psa?: number;
  ca125?: number;

  // 血常规
  wbc?: number;
  rbc?: number;
  hematocrit?: number;
  mcv?: number;
  mch?: number;
  mchc?: number;
  rdw_cv?: number;
  esr?: number;
  platelet?: number;
  neutrophils_ratio?: number;
  lymphocytes_ratio?: number;
  monocytes_ratio?: number;
  eosinophils_ratio?: number;
  basophils_ratio?: number;
  // 绝对值
  neutrophils_abs?: number;
  lymphocytes_abs?: number;
  monocytes_abs?: number;
  eosinophils_abs?: number;
  basophils_abs?: number;

  // 尿检
  urine_color?: string;
  urine_ph?: number | string;
  urine_sg?: number | string;
  urine_protein?: string | number;
  urine_glucose?: string | number;
  urine_bilirubin?: string | number;
  urine_urobilinogen?: string | number;
  urine_ketone?: string | number;
  urine_nitrite?: string | number;
  urine_blood?: string | number;
  urine_leukocytes?: string | number;
  urine_rbc?: string | number;
  urine_epithelial?: string;
  urine_bacteria?: string;

  // 其他
  abnormal_findings?: string[];
  recommendations?: string[];
}

interface HealthDataDisplayProps {
  data: HealthData;
}

const indicators = [
  { key: 'blood_group', label: '血型', unit: '', normal: '', category: '基础信息' },

  { key: 'ferritin', label: '铁蛋白', unit: 'ng/mL', normal: '12-300', category: '基础营养 & 贫血' },
  { key: 'serum_iron', label: '血清铁', unit: 'ug/dL', normal: '60-170', category: '基础营养 & 贫血' },
  { key: 'vitamin_d', label: '维生素D', unit: 'ng/mL', normal: '30-100', category: '基础营养 & 贫血' },
  { key: 'vitamin_b12', label: '维生素B12', unit: 'pg/mL', normal: '200-900', category: '基础营养 & 贫血' },
  { key: 'folic_acid', label: '叶酸', unit: 'ng/mL', normal: '2.7-17', category: '基础营养 & 贫血' },

  { key: 'wbc', label: '白细胞 (WBC)', unit: '10^9/L', normal: '4.0-10.0', category: '血常规 (CBC)' },
  { key: 'rbc', label: '红细胞 (RBC)', unit: '10^12/L', normal: '3.5-5.5', category: '血常规 (CBC)' },
  { key: 'hemoglobin', label: '血红蛋白 (HGB)', unit: 'g/dL', normal: '12-16', category: '血常规 (CBC)' },
  { key: 'hematocrit', label: '红细胞压积 (HCT)', unit: '%', normal: '36-50', category: '血常规 (CBC)' },
  { key: 'mcv', label: '平均红细胞体积 (MCV)', unit: 'fL', normal: '80-100', category: '血常规 (CBC)' },
  { key: 'mch', label: '平均红细胞血红蛋白量', unit: 'pg', normal: '27-31', category: '血常规 (CBC)' },
  { key: 'mchc', label: '平均红细胞血红蛋白浓度', unit: 'g/dL', normal: '32-36', category: '血常规 (CBC)' },
  { key: 'rdw_cv', label: 'RDW-CV (红细胞分布宽度)', unit: '%', normal: '11.5-14.5', category: '血常规 (CBC)' },
  { key: 'esr', label: '血沉 (ESR)', unit: 'mm/h', normal: '0-20', category: '血常规 (CBC)' },
  { key: 'platelet', label: '血小板 (PLT)', unit: '10^9/L', normal: '150-450', category: '血常规 (CBC)' },

  // 细胞分类 (百分比)
  { key: 'neutrophils_ratio', label: '中性粒细胞 %', unit: '%', normal: '40-75', category: '血常规 (CBC)' },
  { key: 'lymphocytes_ratio', label: '淋巴细胞 %', unit: '%', normal: '20-45', category: '血常规 (CBC)' },
  { key: 'monocytes_ratio', label: '单核细胞 %', unit: '%', normal: '2-10', category: '血常规 (CBC)' },
  { key: 'eosinophils_ratio', label: '嗜酸性粒细胞 %', unit: '%', normal: '0.5-5', category: '血常规 (CBC)' },
  { key: 'basophils_ratio', label: '嗜碱性粒细胞 %', unit: '%', normal: '0-1', category: '血常规 (CBC)' },

  // 细胞分类 (绝对值)
  { key: 'neutrophils_abs', label: '中性粒细胞 #', unit: '10^9/L', normal: '2.0-7.0', category: '血常规 (CBC)' },
  { key: 'lymphocytes_abs', label: '淋巴细胞 #', unit: '10^9/L', normal: '0.8-4.0', category: '血常规 (CBC)' },
  { key: 'monocytes_abs', label: '单核细胞 #', unit: '10^9/L', normal: '0.12-1.2', category: '血常规 (CBC)' },
  { key: 'eosinophils_abs', label: '嗜酸性粒细胞 #', unit: '10^9/L', normal: '0.02-0.5', category: '血常规 (CBC)' },
  { key: 'basophils_abs', label: '嗜碱性粒细胞 #', unit: '10^9/L', normal: '0-0.1', category: '血常规 (CBC)' },

  { key: 'fasting_glucose', label: '空腹血糖', unit: 'mg/dL', normal: '70-100', category: '血糖' },
  { key: 'hba1c', label: '糖化血红蛋白', unit: '%', normal: '<5.7', category: '血糖' },

  { key: 'total_cholesterol', label: '总胆固醇', unit: 'mg/dL', normal: '<200', category: '血脂' },
  { key: 'ldl', label: 'LDL胆固醇', unit: 'mg/dL', normal: '<100', category: '血脂' },
  { key: 'hdl', label: 'HDL胆固醇', unit: 'mg/dL', normal: '>40', category: '血脂' },
  { key: 'triglycerides', label: '甘油三酯', unit: 'mg/dL', normal: '<150', category: '血脂' },
  { key: 'chol_hdl_ratio', label: 'CHOL/HDL 比值', unit: '', normal: '<5.0', category: '血脂' },

  { key: 'total_protein', label: '总蛋白', unit: 'g/L', normal: '60-80', category: '肝功能' },
  { key: 'albumin', label: '白蛋白', unit: 'g/L', normal: '35-55', category: '肝功能' },
  { key: 'globulin', label: '球蛋白', unit: 'g/L', normal: '20-30', category: '肝功能' },
  { key: 'ag_ratio', label: '白球比 (A/G)', unit: '', normal: '1.0-2.5', category: '肝功能' },
  { key: 'alt', label: 'ALT (谷丙转氨酶)', unit: 'U/L', normal: '<40', category: '肝功能' },
  { key: 'ast', label: 'AST (谷草转氨酶)', unit: 'U/L', normal: '<40', category: '肝功能' },
  { key: 'total_bilirubin', label: '总胆红素', unit: 'umol/L', normal: '<21', category: '肝功能' },
  { key: 'direct_bilirubin', label: '直接胆红素', unit: 'umol/L', normal: '<7', category: '肝功能' },
  { key: 'indirect_bilirubin', label: '间接胆红素', unit: 'umol/L', normal: '<14', category: '肝功能' },
  { key: 'gamma_gt', label: 'GGT', unit: 'U/L', normal: '<50', category: '肝功能' },
  { key: 'alkaline_phosphatase', label: 'ALP', unit: 'U/L', normal: '40-150', category: '肝功能' },

  { key: 'creatinine', label: '肌酐', unit: 'mg/dL', normal: '0.6-1.2', category: '肾功能' },
  { key: 'uric_acid', label: '尿酸', unit: 'mg/dL', normal: '3.5-7.2', category: '肾功能' },
  { key: 'urea', label: '尿素 (Urea/BUN)', unit: 'mg/dL', normal: '7-20', category: '肾功能' },
  { key: 'e_gfr', label: 'eGFR', unit: 'mL/min', normal: '>90', category: '肾功能' },

  { key: 'calcium', label: '钙 (Calcium)', unit: 'mg/dL', normal: '8.5-10.2', category: '骨骼与代谢' },
  { key: 'phosphorus', label: '磷 (Phosphorus)', unit: 'mg/dL', normal: '2.5-4.5', category: '骨骼与代谢' },

  { key: 'potassium', label: '钾 (Potassium)', unit: 'mmol/L', normal: '3.5-5.0', category: '电解质' },
  { key: 'sodium', label: '钠 (Sodium)', unit: 'mmol/L', normal: '135-145', category: '电解质' },
  { key: 'chloride', label: '氯 (Chloride)', unit: 'mmol/L', normal: '96-106', category: '电解质' },

  { key: 'tsh', label: 'TSH', unit: 'mIU/L', normal: '0.4-4.0', category: '甲状腺' },
  { key: 'free_t4', label: 'Free T4', unit: 'pmol/L', normal: '12-22', category: '甲状腺' },

  { key: 'cea', label: 'CEA (癌胚)', unit: 'ng/mL', normal: '<5.0', category: '肿瘤标记物' },
  { key: 'afp', label: 'AFP (甲胎)', unit: 'ng/mL', normal: '<7.0', category: '肿瘤标记物' },
  { key: 'psa', label: 'PSA (前列腺)', unit: 'ng/mL', normal: '<4.0', category: '肿瘤标记物' },
  { key: 'ca125', label: 'CA125 (卵巢)', unit: 'U/mL', normal: '<35', category: '肿瘤标记物' },

  { key: 'urine_color', label: '尿液颜色', unit: '', normal: 'Yellow', category: '尿检' },
  { key: 'urine_ph', label: '尿液 pH', unit: '', normal: '5.0-8.0', category: '尿检' },
  { key: 'urine_sg', label: '尿比重', unit: '', normal: '1.005-1.030', category: '尿检' },
  { key: 'urine_protein', label: '尿蛋白', unit: '', normal: 'Negative', category: '尿检' },
  { key: 'urine_glucose', label: '尿糖', unit: '', normal: 'Negative', category: '尿检' },
  { key: 'urine_urobilinogen', label: '尿胆原', unit: '', normal: 'Normal', category: '尿检' },
  { key: 'urine_blood', label: '潜血', unit: '', normal: 'Negative', category: '尿检' },
  { key: 'urine_leukocytes', label: '尿白细胞', unit: '', normal: 'Negative', category: '尿检' },
  { key: 'urine_rbc', label: '尿红细胞', unit: '', normal: '0-3', category: '尿检' },
  { key: 'urine_epithelial', label: '上皮细胞', unit: '', normal: 'Rare', category: '尿检' },
  { key: 'urine_bacteria', label: '细菌', unit: '', normal: 'None', category: '尿检' },
];

/**
 * 解析正常范围并判断数值状态
 * 支持:
 * 1. 纯数字比较 (e.g. 5.5 in 4-10)
 * 2. 范围字符串解析 (e.g. "4.0-10.0", "<200", ">90")
 * 3. 定性描述 (e.g. "Negative" vs "Positive", "阴性" vs "阳性")
 */
function getValueStatus(value: number | string, normalRange: string): 'low' | 'high' | 'normal' {
  // 1. 尝试将值转为数字处理
  let numVal = NaN;
  if (typeof value === 'number') {
    numVal = value;
  } else if (typeof value === 'string') {
    // 尝试解析 "6.0", "1.015" 等纯数字字符串
    if (/^[\d.]+$/.test(value)) {
      numVal = parseFloat(value);
    }
  }

  const trimmedRange = normalRange.trim();

  // 如果成功解析出数字，优先尝试数字范围判断
  if (!isNaN(numVal)) {
    // 处理 "<X" 格式 (如 <200)
    if (trimmedRange.startsWith('<')) {
      const max = parseFloat(trimmedRange.slice(1));
      if (!isNaN(max)) return numVal >= max ? 'high' : 'normal';
    }
    // 处理 ">X" 格式 (如 >40)
    if (trimmedRange.startsWith('>')) {
      const min = parseFloat(trimmedRange.slice(1));
      if (!isNaN(min)) return numVal <= min ? 'low' : 'normal';
    }
    // 处理 "X-Y" 范围格式 (如 12-16)
    const rangeMatch = trimmedRange.match(/^([\d.]+)\s*[-–]\s*([\d.]+)$/);
    if (rangeMatch) {
      const min = parseFloat(rangeMatch[1]);
      const max = parseFloat(rangeMatch[2]);
      if (!isNaN(min) && !isNaN(max)) {
        if (numVal < min) return 'low';
        if (numVal > max) return 'high';
        return 'normal';
      }
    }
  }

  // 2. 如果无法按数字处理，或数字逻辑未涵盖（如 fallback），则进行定性判断
  if (typeof value === 'string') {
    const v = value.toLowerCase().trim();
    const n = trimmedRange.toLowerCase();

    // 如果正常范围指明是阴性
    if (n.includes('negative') || n.includes('neg') || n.includes('阴性') || n.includes('-')) {
      // 检查异常关键词：阳性, Positive, +
      if (v.includes('positive') || v.includes('pos') || v.includes('阳性') || v.includes('+')) {
        return 'high';
      }
      // 检查是否是大于0的数字 (例如 "30 mg/dL" for protein when normal is negative)
      const parsed = parseFloat(v);
      if (!isNaN(parsed) && parsed > 0) {
        return 'high';
      }
    }
  }

  return 'normal';
}

function StatusIndicator({ status }: { status: 'low' | 'high' | 'normal' }) {
  if (status === 'low') {
    return <span className="text-red-500 font-bold ml-1">↓</span>;
  }
  if (status === 'high') {
    return <span className="text-red-500 font-bold ml-1">↑</span>;
  }
  return <span className="text-green-500 font-bold ml-1">✓</span>;
}

export function HealthDataDisplay({ data }: HealthDataDisplayProps) {
  // 按类别分组
  const groupedData = indicators.reduce((acc, indicator) => {
    const value = data[indicator.key as keyof HealthData];
    if (value !== null && value !== undefined) {
      if (!acc[indicator.category]) {
        acc[indicator.category] = [];
      }
      acc[indicator.category].push({
        ...indicator,
        value: value
      });
    }
    return acc;
  }, {} as Record<string, any[]>);

  if (Object.keys(groupedData).length === 0 && !data.abnormal_findings?.length) {
    return null;
  }

  return (
    <div className="mt-6 bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* 自定义滚动条样式 */}
      <style jsx>{`
        .health-scroll::-webkit-scrollbar {
          width: 4px;
        }
        .health-scroll::-webkit-scrollbar-track {
          background: transparent;
        }
        .health-scroll::-webkit-scrollbar-thumb {
          background: rgba(156, 163, 175, 0.25);
          border-radius: 9999px;
          transition: background 0.2s;
        }
        .health-scroll:hover::-webkit-scrollbar-thumb {
          background: rgba(156, 163, 175, 0.5);
        }
        .health-scroll::-webkit-scrollbar-thumb:hover {
          background: rgba(107, 114, 128, 0.7);
        }
        /* Firefox */
        .health-scroll {
          scrollbar-width: thin;
          scrollbar-color: rgba(156, 163, 175, 0.25) transparent;
        }
        .health-scroll:hover {
          scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
        }
      `}</style>

      {/* 固定标题 */}
      <div className="px-6 pt-6 pb-3">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          化验值数据
          <span className="text-xs font-normal text-gray-400 ml-auto">
            {Object.values(groupedData).reduce((sum, items) => sum + items.length, 0)} 项指标
          </span>
        </h3>
      </div>

      {/* 可滚动数据区域 */}
      <div className="health-scroll max-h-[60vh] overflow-y-auto px-6 pb-2">
        <div className="space-y-1">
          {Object.entries(groupedData).map(([category, items]) => (
            <div key={category}>
              {/* 吸顶分类标题 */}
              <div
                className="sticky top-0 z-10 -mx-1 px-1 pt-3 pb-2 mb-2"
                style={{
                  background: 'linear-gradient(to bottom, rgba(255,255,255,0.95) 70%, rgba(255,255,255,0))',
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                }}
              >
                <div className="flex items-center gap-2">
                  <div className="w-1 h-4 bg-blue-500 rounded-full"></div>
                  <h4 className="text-sm font-bold text-gray-800 tracking-wide">
                    {category}
                  </h4>
                  <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full">
                    {items.length}
                  </span>
                  <div className="flex-1 h-px bg-gradient-to-r from-gray-200 to-transparent"></div>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
                {items.map((item) => {
                  const status = getValueStatus(item.value, item.normal);
                  const isAbnormal = status !== 'normal';

                  return (
                    <div
                      key={item.key}
                      className={`
                        flex items-center justify-between px-3 py-2.5 rounded-lg
                        transition-all duration-150 hover:shadow-sm
                        ${isAbnormal
                          ? 'bg-red-50/80 border border-red-200/60 hover:bg-red-50'
                          : 'bg-gray-50/60 hover:bg-gray-100/80'
                        }
                      `}
                    >
                      <div className="min-w-0 flex-1 mr-3">
                        <div className="text-[13px] font-medium text-gray-900 truncate">{item.label}</div>
                        <div className="text-[11px] text-gray-400 mt-0.5">
                          {item.normal && <>正常: {item.normal}{item.unit ? ` ${item.unit}` : ''}</>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <div className="text-right">
                          <div className={`text-base font-bold tabular-nums ${isAbnormal ? 'text-red-600' : 'text-gray-900'}`}>
                            {item.value}
                          </div>
                          {item.unit && (
                            <div className="text-[10px] text-gray-400">{item.unit}</div>
                          )}
                        </div>
                        <StatusIndicator status={status} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 异常发现 — 固定在滚动区域外 */}
      {data.abnormal_findings && data.abnormal_findings.length > 0 && (
        <div className="mx-6 mb-4 p-4 bg-amber-50/80 border border-amber-200/60 rounded-lg">
          <h4 className="text-sm font-bold text-amber-800 mb-2 flex items-center gap-1.5">
            <span>⚠️</span> 异常发现
          </h4>
          <ul className="space-y-1">
            {data.abnormal_findings.map((finding, idx) => (
              <li key={idx} className="text-[13px] text-amber-700 leading-relaxed">• {finding}</li>
            ))}
          </ul>
        </div>
      )}

      {/* AI 建议 — 固定在滚动区域外 */}
      {data.recommendations && data.recommendations.length > 0 && (
        <div className="mx-6 mb-6 p-4 bg-blue-50/80 border border-blue-200/60 rounded-lg">
          <h4 className="text-sm font-bold text-blue-800 mb-2 flex items-center gap-1.5">
            <span>💡</span> 营养补充建议
          </h4>
          <ul className="space-y-1">
            {data.recommendations.map((rec, idx) => (
              <li key={idx} className="text-[13px] text-blue-700 leading-relaxed">• {rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
