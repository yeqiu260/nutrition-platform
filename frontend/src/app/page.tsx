'use client';
import { API_BASE_URL } from '@/lib/api/config';

import React, { useState, useRef, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useLocaleContext } from '@/contexts/LocaleContext';
import { MainPageLanguageSwitcher } from '@/components/MainPageLanguageSwitcher';
import { HealthDataDisplay } from '@/components/HealthDataDisplay';
import { FavoriteButton } from '@/components/FavoriteButton';
import {
  User,
  Upload,
  Camera,
  FileText,
  ChevronRight,
  ChevronLeft,
  X,
  ShoppingCart,
  CheckCircle,
  Eye,
  EyeOff,
  Lock,
  Mail,
  Brain,
  ListFilter,
  FileSearch,
  ArrowRight,
  ShieldCheck,
  FlaskConical
} from 'lucide-react';

/* =========================================
   1. Configuration & Data
   ========================================= */

const supplementsConfig = [
  { id: 'vitamin_d', name: '維他命 D (Vitamin D)', group: '基礎營養｜骨骼與免疫', screeningThreshold: 2, note: '維他命 D 不只關節與骨骼，更是免疫系統的重要開關。長期待在室內、日曬不足的人，常見有不顯性缺乏。', screening: [{ subtitle: '日曬情況', text: '你平均一週有幾天，在不撐傘、沒厚塗防曬的情況下，曬到 10–15 分鐘以上正午陽光？', options: [{ label: '幾乎沒有，長期待在室內', score: 2 }, { label: '一週大約 1–2 天，時間不一定夠', score: 1 }, { label: '一週 3 天以上，日曬算是足夠', score: 0 }] }], detail: [{ subtitle: '骨質與免疫', text: '你是否曾被提醒骨質疏鬆／骨密度偏低，或覺得自己很容易小病不斷（感冒、呼吸道感染）？', options: [{ label: '是，至少有一項情況很明顯', score: 3 }, { label: '有一點，但沒有正式診斷', score: 1 }, { label: '沒有這樣的情況', score: 0 }] }] },
  { id: 'vitamin_b_complex', name: '維他命 B 群 (Vitamin B complex)', group: '基礎營養｜能量與神經', screeningThreshold: 2, note: 'B 群是能量代謝與神經系統的「螺絲釘」，外食多、壓力大又常覺得累的人，常常會有潛在缺口。', screening: [{ subtitle: '疲勞與飲食型態', text: '你是否經常覺得「一整天都很疲倦」，而且三餐多半是外食、麵包、飯麵、甜飲為主？', options: [{ label: '非常符合，幾乎天天如此', score: 2 }, { label: '部分符合，偶爾會這樣', score: 1 }, { label: '不太符合，飲食與精神都還好', score: 0 }] }], detail: [{ subtitle: '神經與專注', text: '你是否有手腳偶爾刺麻、很難集中精神、情緒容易低落或緊張，但又說不上有明確精神科診斷？', options: [{ label: '是，而且已經持續一段時間', score: 3 }, { label: '有一點，但不算嚴重', score: 1 }, { label: '幾乎沒有這些情況', score: 0 }] }] },
  { id: 'vitamin_c', name: '維他命 C (Vitamin C)', group: '基礎營養｜抗氧化與免疫', screeningThreshold: 2, note: '維他命 C 是膠原蛋白生成與免疫的基本原料，蔬果明顯不足又常抽菸或曝露在二手煙的人，需求會更高。', screening: [{ subtitle: '蔬果份量', text: '你每天大約會吃到幾份新鮮水果或蔬菜？（一碗菜／一顆中型水果算一份）', options: [{ label: '大多數日子 0–1 份，幾乎不太吃', score: 2 }, { label: '大約 2 份，勉強有吃到', score: 1 }, { label: '3 份以上，基本都有刻意吃', score: 0 }] }], detail: [{ subtitle: '牙齦與傷口', text: '你是否覺得牙齦容易流血、或小傷口、刮傷的癒合速度偏慢？（不含明顯牙周病或抽煙造成）', options: [{ label: '是，經常這樣', score: 3 }, { label: '偶爾會，但不明顯', score: 1 }, { label: '沒有這類情況', score: 0 }] }] },
  { id: 'calcium', name: '鈣 (Calcium)', group: '礦物質｜骨骼與牙齒', screeningThreshold: 2, note: '鈣質優先從食物來補，若本身飲食鈣攝取不足又有骨質風險，才考慮補充劑配合維他命 D。', screening: [{ subtitle: '含鈣食物', text: '你平常一天大約會攝取多少含鈣食物（牛奶、乳酪、優格、含鈣豆腐等）？', options: [{ label: '幾乎沒有或非常少', score: 2 }, { label: '偶爾有，但不固定', score: 1 }, { label: '幾乎每天都有 1–2 份以上', score: 0 }] }], detail: [{ subtitle: '骨質與家族史', text: '你是否有骨質疏鬆家族史、曾做骨密度檢查偏低，或曾因輕微撞擊就骨折？', options: [{ label: '是，至少有一項明顯符合', score: 3 }, { label: '好像有點風險，但不太確定', score: 1 }, { label: '沒有上述情況', score: 0 }] }] },
  { id: 'magnesium', name: '鎂 (Magnesium)', group: '礦物質｜肌肉放鬆與睡眠', screeningThreshold: 2, note: '鎂參與三百多種酵素反應，是「放鬆系」的關鍵角色，對抽筋、肌肉緊繃、睡不好的人常有幫助。', screening: [{ subtitle: '抽筋與睡眠', text: '你是否經常出現小腿抽筋、眼皮跳，或覺得很難放鬆入睡、睡前身體很緊繃？', options: [{ label: '是，經常出現而且困擾', score: 2 }, { label: '偶爾有，但還可以忍受', score: 1 }, { label: '幾乎沒有這些問題', score: 0 }] }], detail: [{ subtitle: '飲食與壓力', text: '你是否很少吃深綠色蔬菜、堅果、全穀類，且自覺壓力偏大、常常感到焦慮或緊張？', options: [{ label: '非常符合我的狀況', score: 3 }, { label: '部分符合', score: 1 }, { label: '不太符合', score: 0 }] }] },
  { id: 'iron', name: '鐵 (Iron)', group: '微量元素｜貧血與疲勞', screeningThreshold: 2, note: '鐵劑補充前最好做血液檢查（血清鐵蛋白），避免不必要的過量。素食者與經血量多的女性是高風險群。', screening: [{ subtitle: '疲勞與臉色', text: '你是否常常覺得很累、容易頭晕，且被人說臉色或嘴唇偏白？', options: [{ label: '是，而且已經持續一段時間', score: 2 }, { label: '有一點這種感覺', score: 1 }, { label: '不太會，精神與臉色都還好', score: 0 }] }], detail: [{ subtitle: '飲食與失血', text: '你平常幾乎不吃紅肉或內臟，且（如有月經）自覺經血量偏多或經期常超過 7 天嗎？', options: [{ label: '是，飲食少鐵又經血量偏多', score: 3 }, { label: '部分符合／不太確定', score: 1 }, { label: '不符合／不適用', score: 0 }] }] },
  { id: 'zinc', name: '鋅 (Zinc)', group: '微量元素｜免疫與皮膚', screeningThreshold: 2, note: '鋅與免疫、防禦力與傷口癒合高度相關，過量則會干擾銅的吸收，需注意使用時間與劑量。', screening: [{ subtitle: '免疫與味覺', text: '你是否覺得自己容易感冒、傷口癒合慢，或味覺比以前遲鈍？', options: [{ label: '是，這些情況經常出現', score: 2 }, { label: '偶爾覺得有一點', score: 1 }, { label: '幾乎沒有這些狀況', score: 0 }] }], detail: [{ subtitle: '飲食型態', text: '你的飲食是否以白飯、麵包為主，很少吃海鮮、紅肉或堅果？（或長期素食但未特別規劃蛋白質來源）', options: [{ label: '非常符合', score: 3 }, { label: '部分符合', score: 1 }, { label: '不太符合', score: 0 }] }] },
  { id: 'omega3', name: 'Omega-3 魚油（EPA / DHA）', group: '必需脂肪酸｜心血管與發炎調節', screeningThreshold: 2, note: '若幾乎不吃深海魚，Omega-3 常是優先度很高的一條補充線，與心血管、發炎與腦部功能都有關。', screening: [{ subtitle: '深海魚攝取', text: '你每週大約吃幾次高油脂魚類（例如三文魚、鯖魚、沙丁魚）？', options: [{ label: '幾乎不吃或一個月不到一次', score: 2 }, { label: '每週大約 1 次', score: 1 }, { label: '每週至少 2 次以上', score: 0 }] }], detail: [{ subtitle: '心血管與關節', text: '你是否有心血管風險（高血脂、家族心臟病史），或經常關節痠痛、體內發炎感？', options: [{ label: '是，至少有一項很明顯', score: 3 }, { label: '有一點，但不算嚴重', score: 1 }, { label: '沒有這些情況', score: 0 }] }] },
  { id: 'whey_protein', name: '乳清蛋白 (Whey protein)', group: '蛋白質｜運動恢復與肌肉維持', screeningThreshold: 2, note: '關鍵是「一天總蛋白質量」有沒有達標，乳清只是讓你更容易補齊缺口，對有在重訓的人特別實用。', screening: [{ subtitle: '蛋白質總量', text: '以你目前的飲食，你覺得一天大多數餐「都有明顯的肉／蛋／豆／奶」嗎？', options: [{ label: '很多餐都只有飯麵＋少量配菜，應該不太夠', score: 2 }, { label: '勉強還可以，但不是每餐都足夠', score: 1 }, { label: '我有刻意確保每餐有蛋白質主角', score: 0 }] }], detail: [{ subtitle: '運動與目標', text: '你目前是否有固定做阻力訓練（例如健身房重訓、一週至少 2 次），並希望維持或增加肌肉量？', options: [{ label: '是，持續規律訓練並以增肌為目標', score: 3 }, { label: '偶爾訓練，但不太固定', score: 1 }, { label: '幾乎沒有做重訓或阻力運動', score: 0 }] }] },
  { id: 'plant_protein', name: '植物蛋白 (Plant protein)', group: '蛋白質｜素食蛋白來源', screeningThreshold: 2, note: '對純素或偏素、又想兼顧肌肉與體重管理的人，是很方便的蛋白質來源。', screening: [{ subtitle: '素食與蛋白來源', text: '你是否為全素／蛋奶素，或幾乎不吃肉類，但又沒有特別規劃豆類、豆腐等蛋白質來源？', options: [{ label: '非常符合，我是偏素又沒特別算蛋白質', score: 2 }, { label: '部分符合，我吃肉不多', score: 1 }, { label: '不符合，我吃肉類或蛋奶都不少', score: 0 }] }], detail: [{ subtitle: '體重與肌肉', text: '你是否希望在不增加太多脂肪的情況下維持／增加肌肉，或曾被提醒有肌少症風險？', options: [{ label: '是，這正是我在意的', score: 3 }, { label: '有一點在意，但沒有很積極', score: 1 }, { label: '目前沒有特別肌肉／體重目標', score: 0 }] }] },
  { id: 'creatine', name: '肌酸 (Creatine monohydrate)', group: '運動表現｜力量與爆發力', screeningThreshold: 2, note: '研究最扎實的運動補充品之一，對力量、爆發力與部分認知表現都有好處，安全性也很高。', screening: [{ subtitle: '訓練型態', text: '你是否每週至少 2–3 次進行重訓或需要爆發力的訓練（例如深蹲、硬舉、衝刺等）？', options: [{ label: '是，規律做這類訓練', score: 2 }, { label: '偶爾會這樣訓練', score: 1 }, { label: '幾乎沒有做高強度／爆發力訓練', score: 0 }] }], detail: [{ subtitle: '進步瓶頸', text: '你是否覺得訓練重量或次數已經卡關一陣子，想要在力量或爆發力上再向上突破？', options: [{ label: '是，最近明顯卡關', score: 3 }, { label: '有一點，但還好', score: 1 }, { label: '目前沒有覺得卡關', score: 0 }] }] },
  { id: 'joint_formula', name: '關節配方（葡萄糖胺 / 軟骨素 / MSM）', group: '機能保健｜骨關節健康', screeningThreshold: 2, note: '對已經有退化性關節炎症狀的人，比對年輕健康關節「預防吃」更有證據與價值。', screening: [{ subtitle: '關節症狀', text: '你是否長期（超過 3 個月）感到膝蓋、髖關節或手指關節僵硬、疼痛，尤其是早上起床或久坐後？', options: [{ label: '是，而且已經困擾一段時間', score: 2 }, { label: '偶爾會，有一點不舒服', score: 1 }, { label: '幾乎沒有關節不適', score: 0 }] }], detail: [{ subtitle: '診斷與年齡', text: '你是否已被醫師診斷為退化性關節炎，或年齡超過 45 歲且關節負重工作／運動較多？', options: [{ label: '是，符合其中一項以上', score: 3 }, { label: '可能有一點風險，但不確定', score: 1 }, { label: '沒有上述情況', score: 0 }] }] },
  { id: 'probiotics', name: '益生菌 (Probiotics)', group: '腸道與消化｜腸道菌相', screeningThreshold: 2, note: '對抗生素後腹瀉、腸躁症族群最有研究支持，一般健康人不一定需要長期吃。', screening: [{ subtitle: '腸道狀況', text: '你是否常常腹脹、腹瀉與便秘交替、或大便型態很不穩定（時硬時稀）？', options: [{ label: '是，腸胃容易鬧脾氣', score: 2 }, { label: '偶爾會這樣', score: 1 }, { label: '腸胃大致穩定', score: 0 }] }], detail: [{ subtitle: '抗生素與診斷', text: '過去一年內，你是否有多次使用抗生素，或被醫師懷疑／診斷為腸躁症（IBS）？', options: [{ label: '是，有這些情況', score: 3 }, { label: '不確定／只有一點點', score: 1 }, { label: '都沒有', score: 0 }] }] },
  { id: 'fiber_soluble', name: '可溶性膳食纖維（菊糖 / 洋車前子）', group: '腸道與代謝｜纖維', screeningThreshold: 2, note: '蔬果與全穀嚴重不足，又有便秘或血脂血糖問題時，很值得考慮用纖維來輔助。', screening: [{ subtitle: '飲食與排便', text: '你是否蔬果、全穀吃得很少，且常有排便困難、便秘或排便不順的情況？', options: [{ label: '是，描述非常貼切', score: 2 }, { label: '偶爾會便秘', score: 1 }, { label: '排便大致正常，蔬果也吃得夠', score: 0 }] }], detail: [{ subtitle: '血脂與血糖', text: '你是否曾被醫師提醒血脂／血糖偏高，或有糖尿病前期風險？', options: [{ label: '是，有被正式提醒', score: 3 }, { label: '還沒有正式說，但體重／家族史讓我有點擔心', score: 1 }, { label: '目前沒有相關問題', score: 0 }] }] },
  { id: 'melatonin', name: '褪黑激素 (Melatonin)', group: '睡眠｜入睡時間', screeningThreshold: 2, note: '適合「很難入睡」或時差問題，不是所有失眠類型都適用，也不建議長期大劑量自己吃。', screening: [{ subtitle: '睡眠型態', text: '你睡覺最大的困擾是「躺下去很久才睡得著」，而不是半夜常常醒來嗎？', options: [{ label: '是，我主要是很難入睡', score: 2 }, { label: '兩種問題都有一點', score: 1 }, { label: '我比較像是半夜常醒／早醒', score: 0 }] }], detail: [{ subtitle: '作息與時差', text: '你是否常需要輪班、跨時區旅行，或經常熬夜滑手機到很晚才睡？', options: [{ label: '是，作息非常不規律', score: 3 }, { label: '有時候會這樣', score: 1 }, { label: '作息相對規律', score: 0 }] }] },
  { id: 'theanine_gaba', name: '放鬆配方（L-茶胺酸 / GABA 等）', group: '睡眠與壓力｜放鬆感', screeningThreshold: 2, note: '偏向「幫你放鬆」而不是直接敲昏，適合腦袋停不下來、壓力大又還不到需要安眠藥的族群。', screening: [{ subtitle: '緊張與腦內小劇場', text: '你是否常常因為腦中想法停不下來、壓力很大，而導致難以放鬆或入睡？', options: [{ label: '是，腦袋很難關機', score: 2 }, { label: '偶爾會這樣', score: 1 }, { label: '不太會受這種影響', score: 0 }] }], detail: [{ subtitle: '生活壓力', text: '最近一兩年，你覺得自己的整體生活壓力屬於哪個程度？', options: [{ label: '非常大，長期處於緊繃狀態', score: 3 }, { label: '中等，有壓力但還撐得住', score: 1 }, { label: '壓力不大，整體還算輕鬆', score: 0 }] }] },
  { id: 'herbal_sleep', name: '草本助眠（纈草根 / 西番蓮 等）', group: '睡眠與壓力｜草本配方', screeningThreshold: 2, note: '適合輕中度失眠、想先試「草本、非處方」的人。有在吃安眠藥的人，務必要先問主診醫生。', screening: [{ subtitle: '失眠程度', text: '你的睡眠問題屬於「輕度到中度」，還不至於每天都需要處方安眠藥嗎？', options: [{ label: '是，目前算輕中度失眠', score: 2 }, { label: '我已經在吃處方安眠藥', score: 0 }, { label: '沒有明顯失眠問題', score: 0 }] }], detail: [{ subtitle: '偏好與安全', text: '你是否特別希望先嘗試「草本、非處方」的方式來幫助放鬆與入睡？', options: [{ label: '是，我比較喜歡先試溫和的', score: 3 }, { label: '沒有特別偏好', score: 1 }, { label: '不太想吃任何跟睡眠有關的東西', score: 0 }] }] },
  { id: 'eye_lutein_zeaxanthin', name: '護眼配方（葉黃素 / 玉米黃素）', group: '眼睛健康｜黃斑部保護', screeningThreshold: 2, note: '對長時間用眼、高藍光暴露或家族有黃斑部病變的人，有相對完整的臨床證據支持。', screening: [{ subtitle: '螢幕時間', text: '你平均每天使用電腦＋手機螢幕的時間，大約多久？', options: [{ label: '超過 8 小時，是重度用眼族', score: 2 }, { label: '大約 4–8 小時', score: 1 }, { label: '少於 4 小時', score: 0 }] }], detail: [{ subtitle: '家族史與飲食', text: '家族中是否有人有黃斑部病變，或你平常很少吃深綠色葉菜（菠菜、羽衣甘藍）？', options: [{ label: '是，至少有一項明顯符合', score: 3 }, { label: '可能有一點，但不確定', score: 1 }, { label: '都沒有', score: 0 }] }] },
  { id: 'skin_collagen', name: '皮膚彈力配方（膠原蛋白 等）', group: '皮膚與外觀｜彈性與保濕', screeningThreshold: 2, note: '真正的底層邏輯還是防曬、睡眠與壓力管理，膠原蛋白是加分項，不是時光機。', screening: [{ subtitle: '膚況與在意程度', text: '你是否明顯在意細紋、鬆弛、皮膚乾燥等問題，覺得單靠保養品或睡覺不太夠？', options: [{ label: '是，我很在意這一塊', score: 2 }, { label: '有一點在意', score: 1 }, { label: '目前不太在意', score: 0 }] }], detail: [{ subtitle: '生活型態', text: '你是否常熬夜、工作壓力大、或曾長期曝曬（戶外工作、愛曬太陽）？', options: [{ label: '是，生活型態對皮膚有明顯壓力', score: 3 }, { label: '有一點，但不算太誇張', score: 1 }, { label: '作息與防曬都做得不錯', score: 0 }] }] },
  { id: 'hair_nails_biotin', name: '頭髮／指甲配方（含生物素 Biotin）', group: '皮膚與外觀｜頭髮與指甲', screeningThreshold: 3, note: '對沒有明確生物素缺乏的人，效果證據有限，而且高劑量會干擾某些血液檢驗結果。', screening: [{ subtitle: '實際問題', text: '你是否有明顯的病理性脆甲（很容易分裂斷裂）、或異常嚴重的掉髮，已讓你強烈困擾？', options: [{ label: '是，狀況很嚴重', score: 3 }, { label: '有一點，但還在可接受範圍', score: 1 }, { label: '沒有特別這樣', score: 0 }] }], detail: [{ subtitle: '醫療評估', text: '你是否曾被醫師懷疑／診斷有營養相關缺乏（如生物素）、或已排除甲狀腺等內分泌問題？', options: [{ label: '是，有被這樣評估過', score: 3 }, { label: '還沒有正式檢查過', score: 1 }, { label: '沒有相關檢查／診斷', score: 0 }] }] },
  { id: 'blood_sugar_mix', name: '血糖／代謝配方（ALA / 鉻 / 肉桂）', group: '血糖與代謝｜輔助型補充品', screeningThreshold: 3, note: '重點永遠是飲食與運動，這一組比較像「加強版配角」，對糖尿病神經病變有較多 ALA 的證據。', screening: [{ subtitle: '血糖狀況', text: '你是否已被診斷為第二型糖尿病，或被醫師提醒血糖偏高（糖尿病前期）？', options: [{ label: '是，有相關診斷／明確提醒', score: 3 }, { label: '還沒有診斷，但體重與家族史讓我擔心', score: 1 }, { label: '目前沒有這方面問題', score: 0 }] }], detail: [{ subtitle: '神經症狀', text: '你是否有腳底灼熱、刺痛或麻木等可能與糖尿病神經病變有關的症狀？', options: [{ label: '是，症狀明顯且醫師也提過', score: 3 }, { label: '有一點，不太確定原因', score: 1 }, { label: '沒有這些症狀', score: 0 }] }] },
  { id: 'liver_support_nac_milk', name: '肝臟保護（NAC / 乳薊 等）', group: '肝臟與排毒｜輔助型補充品', screeningThreshold: 3, note: '脂肪肝或肝指數偏高時，生活與飲食調整是主角，這類補充品是可以討論的加分項。', screening: [{ subtitle: '肝臟負擔', text: '你是否有脂肪肝、肝指數偏高，或經常大量飲酒、長期服用對肝臟有負擔的藥物？', options: [{ label: '是，醫師有特別提醒過肝臟問題', score: 3 }, { label: '偶爾飲酒，指數大致正常', score: 1 }, { label: '沒有這些狀況', score: 0 }] }], detail: [{ subtitle: '醫師追蹤', text: '你是否有固定追蹤肝功能，並與醫師討論過可以使用這類保健品？', options: [{ label: '是，醫師也同意我輔助使用', score: 3 }, { label: '還沒特別問過醫師', score: 1 }, { label: '目前沒有追蹤／沒有諮詢過', score: 0 }] }] },
  { id: 'coq10', name: '輔酶 Q10 (CoQ10)', group: '心血管與能量｜線粒體功能', screeningThreshold: 2, note: '特別適合正在服用 Statin 類降膽固醇藥物，又出現肌肉痠痛或能量感下降的人。', screening: [{ subtitle: '用藥史', text: '你目前是否正在服用醫師開立的降膽固醇藥（Statin 類，例如 Atorvastatin 等）？', options: [{ label: '是，已服用一段時間', score: 2 }, { label: '曾經吃過一小段時間', score: 1 }, { label: '沒有服用過 Statin 類藥物', score: 0 }] }], detail: [{ subtitle: '肌肉與心臟', text: '服用降膽固醇藥後，你是否有不明原因的肌肉痠痛／無力，或本身有心臟收縮功能偏弱的問題？', options: [{ label: '是，符合其中一項以上', score: 3 }, { label: '有一點痠軟，但不太確定關聯', score: 1 }, { label: '沒有這些問題', score: 0 }] }] },
  { id: 'red_yeast_rice', name: '紅麴 (Red yeast rice)', group: '心血管｜類 Statin 降血脂', screeningThreshold: 3, note: '紅麴內含成分與部份降膽固醇藥物類似，實際上強度已經很接近「藥物」，務必在醫師監督下使用。', screening: [{ subtitle: '膽固醇狀況', text: '你是否已有明確的高膽固醇血症診斷，但仍在尋找「非處方藥」方式來輔助控制？', options: [{ label: '是，符合這個狀況', score: 3 }, { label: '有一點擔心膽固醇，但還沒診斷', score: 1 }, { label: '目前沒有相關問題', score: 0 }] }], detail: [{ subtitle: '肝功能與用藥', text: '你是否曾有肝功能異常、或同時在使用其他可能傷肝的藥物／補充品？', options: [{ label: '是，有這樣的風險，必須特別小心', score: 0 }, { label: '沒有相關問題', score: 2 }, { label: '不確定，沒追蹤過', score: 1 }] }] },
  { id: 'rhodiola', name: '紅景天 (Rhodiola rosea)', group: '壓力與精神表現｜適應原', screeningThreshold: 2, note: '對壓力性疲勞、工作倦怠有一些臨床支持，但若有明顯憂鬱／躁鬱症狀仍需優先找精神科。', screening: [{ subtitle: '壓力型疲勞', text: '你是否長期感到「精神很累、很倦怠」，但睡多少都覺得沒完全恢復？', options: [{ label: '是，非常符合我的感覺', score: 2 }, { label: '偶爾會，但不是一直如此', score: 1 }, { label: '不太會這樣覺得', score: 0 }] }], detail: [{ subtitle: '情緒狀態', text: '你最近是否常覺得心情低落、提不起勁，但還不至於嚴重影響日常功能（或已有安排看診）？', options: [{ label: '是，有明顯情緒困擾且正在努力處理', score: 3 }, { label: '有一點低潮感', score: 1 }, { label: '情緒大致穩定', score: 0 }] }] },
  { id: 'cordyceps', name: '冬蟲夏草 (Cordyceps)', group: '耐力與呼吸｜傳統草本', screeningThreshold: 2, note: '對中老年人或耐力表現有些溫和的幫助，但前提仍是你有在動、有在訓練。', screening: [{ subtitle: '體力與年齡', text: '你是否已屬中高齡，且覺得走路、爬樓梯或運動時容易喘、體力比同齡人差？', options: [{ label: '是，體力明顯比以前差很多', score: 2 }, { label: '有一點，但還能接受', score: 1 }, { label: '體力還算不錯', score: 0 }] }], detail: [{ subtitle: '運動與目標', text: '你是否有規律安排散步／快走／慢跑等運動，並希望逐步提升耐力與恢復速度？', options: [{ label: '是，我正在努力訓練耐力', score: 3 }, { label: '偶爾運動', score: 1 }, { label: '幾乎不運動', score: 0 }] }] },
  { id: 'green_tea_extract', name: '綠茶萃取 (Green tea extract / EGCG)', group: '體重管理與抗氧化', screeningThreshold: 2, note: '在有做飲食與運動前提下，綠茶萃取可以是加分項；高劑量 EGCG 則要注意肝臟安全。', screening: [{ subtitle: '體重與生活型態', text: '你是否 BMI 偏高，想調整體重，但已開始嘗試飲食控制與運動？', options: [{ label: '是，我已經在做飲食＋運動，想再多一點輔助', score: 2 }, { label: '有想減重，但還沒真的開始改生活', score: 1 }, { label: '目前沒有體重管理需求', score: 0 }] }], detail: [{ subtitle: '咖啡因耐受與肝臟', text: '你平常對咖啡因還算能適應，且沒有肝功能異常或相關病史嗎？', options: [{ label: '是，兩者都 OK', score: 3 }, { label: '不太耐咖啡因／肝功能有些問題', score: 0 }, { label: '不確定，需要再確認', score: 1 }] }] },
  { id: 'l_carnitine', name: '左旋肉鹼 (L-carnitine)', group: '脂肪代謝與運動表現', screeningThreshold: 2, note: '對有規律做有氧、以耐力或脂肪代謝為目標的人才有實際幫助，不是「躺著喝就瘦」那種東西。', screening: [{ subtitle: '運動型態', text: '你是否有規律進行 30 分鐘以上的有氧運動（快走、慢跑、單車等），每週至少 3 次？', options: [{ label: '是，規律做這類運動', score: 2 }, { label: '偶爾運動，但不固定', score: 1 }, { label: '幾乎不做有氧運動', score: 0 }] }], detail: [{ subtitle: '飲食與目標', text: '你是否以減脂／提升運動耐力為主要目標，且飲食中紅肉攝取量不高（或是偏素）？', options: [{ label: '是，完全符合', score: 3 }, { label: '部分符合', score: 1 }, { label: '不太符合', score: 0 }] }] },
  { id: 'prenatal_multi', name: '孕婦綜合維他命 (Prenatal vitamins)', group: '族群專用｜孕期與備孕', screeningThreshold: 2, note: '神經管缺陷預防依賴葉酸，通常建議備孕前就開始補，劑量與品牌建議跟產科醫師討論。', screening: [{ subtitle: '人生階段', text: '你目前是否正在懷孕，或計畫在未來 36 個月內懷孕？', options: [{ label: '是，正在懷孕或積極備孕', score: 2 }, { label: '有一點想法，但還不確定時間', score: 1 }, { label: '目前沒有懷孕計畫', score: 0 }] }], detail: [{ subtitle: '飲食與醫師建議', text: '你的飲食是否較難吃到足量蔬菜、鐵質與 DHA，且醫師或護理人員也有建議你補充孕婦專用配方？', options: [{ label: '是，醫護也有建議', score: 3 }, { label: '部分符合，還沒特別問過', score: 1 }, { label: '沒有，飲食很均衡也有規律產檢', score: 0 }] }] },
  { id: 'childrens_multi', name: '兒童綜合維他命', group: '族群專用｜兒童成長', screeningThreshold: 2, note: '偏食小孩的第一線處理仍是飲食教育與家庭餐桌設計，綜合維他命可以暫時補洞。', screening: [{ subtitle: '偏食程度', text: '你是否有照顧的小孩，長期極度偏食（幾乎不吃蔬果或肉類），讓你擔心營養狀況？', options: [{ label: '是，小朋友非常挑食', score: 2 }, { label: '有點挑食，但還吃得下幾種', score: 1 }, { label: '飲食大致正常', score: 0 }] }], detail: [{ subtitle: '生長與專業建議', text: '兒童生長曲線（身高／體重）是否曾被醫護提醒需要注意，或建議可以考慮補充綜合維他命？', options: [{ label: '是，有被特別提醒過', score: 3 }, { label: '沒有正式提醒，但我有一點擔心', score: 1 }, { label: '沒有被提醒也不特別擔心', score: 0 }] }] }
];

// API 响应类型定义
interface ProductRecommendation {
  product_id: string;
  product_name: string;
  why_this_product: string[];
  price?: number;
  currency: string;
  purchase_url: string;
  image_url?: string;
  partner_name?: string;
}

interface AIRecommendationItem {
  rank: number;
  supplement_id: string;
  name: string;
  group: string;
  why: string[];
  safety: string[];
  confidence: number;
  recommended_products: ProductRecommendation[];
}

interface AIRecommendationResponse {
  session_id: string;
  generated_at: string;
  items: AIRecommendationItem[];
  disclaimer: string;
  ai_generated: boolean;
}


/* =========================================
   2. Sub-Components
   ========================================= */

// Header Component
const Header = ({ onRestart, onLogout, isLoggedIn, onLoginClick, view }: {
  onRestart: () => void;
  onLogout?: () => void;
  isLoggedIn: boolean;
  onLoginClick?: () => void;
  view?: string;
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [userEmail, setUserEmail] = useState<string>('');
  const tCommon = useTranslations('common');
  const t = useTranslations('landing');
  const tHeader = useTranslations('header');
  const { locale, setLocale } = useLocaleContext();

  // 从 localStorage 获取用户信息
  useEffect(() => {
    if (typeof window !== 'undefined' && isLoggedIn) {
      const email = localStorage.getItem('user_email') || '';
      setUserEmail(email);
    }
  }, [isLoggedIn]);

  // 获取显示名称（优先显示邮箱前缀，否则显示完整邮箱）
  const displayName = userEmail
    ? (userEmail.includes('@') ? userEmail.split('@')[0] : userEmail)
    : tHeader('user.defaultName');

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
        <div
          className="flex items-center gap-2 cursor-pointer"
          onClick={onRestart}
        >
          <div className="w-8 h-8 bg-yellow-400 rounded-lg flex items-center justify-center font-bold text-gray-900">
            W
          </div>
          <span className="text-xl font-bold tracking-tight text-gray-900">WysikHealth</span>
        </div>

        <div className="flex items-center gap-2">
          {/* 语言切换器 */}
          <MainPageLanguageSwitcher
            currentLocale={locale}
            onLocaleChange={(newLocale) => setLocale(newLocale as 'zh-TW' | 'en')}
          />

          {isLoggedIn ? (
            <div className="relative">
              <button
                className="flex items-center gap-3 hover:bg-gray-100 px-3 py-2 rounded-full transition-colors"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
              >
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-bold text-gray-900">{displayName}</div>
                  <div className="text-xs text-gray-500">{tHeader('user.generalMember')}</div>
                </div>
                <div className="w-9 h-9 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 border border-gray-300">
                  <User size={20} />
                </div>
              </button>

              {isMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50">
                  <a
                    href="/history"
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {tHeader('user.history')}
                  </a>
                  <a
                    href="/favorites"
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {tHeader('user.favorites')}
                  </a>
                  <a href="#" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">{tHeader('user.profile')}</a>
                  <div className="border-t border-gray-100 my-1"></div>
                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      onLogout?.();
                    }}
                    className="w-full text-left block px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    {tCommon('logout')}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-4">
              {view === 'landing' && (
                <div className="hidden md:flex items-center gap-6 mr-4 text-sm font-medium text-gray-600">
                  <button className="hover:text-gray-900" onClick={() => document.getElementById('features-section')?.scrollIntoView({ behavior: 'smooth' })}>{t('nav.features')}</button>
                  <button className="hover:text-gray-900" onClick={onLoginClick}>{t('nav.startQuiz')}</button>
                </div>
              )}
              <button
                onClick={onLoginClick}
                className="text-gray-900 font-bold hover:text-yellow-600 px-2 text-sm"
              >
                {tCommon('login')}
              </button>
              <button
                onClick={onLoginClick}
                className="bg-gray-900 text-white px-4 py-2 rounded-full text-sm font-bold hover:bg-yellow-400 hover:text-gray-900 transition-colors"
              >
                {tCommon('register')}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

// Landing Page Component
const LandingPage = ({ onStartQuiz }: { onStartQuiz: () => void }) => {
  const t = useTranslations('landing');

  return (
    <div className="bg-[#f5f5f7]">
      {/* Hero Section */}
      <section className="relative pt-20 pb-20 sm:pt-32 sm:pb-32 px-4 overflow-hidden">
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 bg-yellow-100 text-yellow-800 px-4 py-1.5 rounded-full text-sm font-bold mb-6">
            <span className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></span>
            {t('badges.newSystem')}
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold text-gray-900 tracking-tight leading-tight mb-6">
            {t('hero.title').split('，')[0]}，<br className="hidden sm:block" />
            {t('hero.title').split('，')[1]}
          </h1>

          <p className="text-lg sm:text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            {t('hero.subtitle')}
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onStartQuiz}
              className="w-full sm:w-auto px-8 py-4 bg-gray-900 text-white text-lg font-bold rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all transform hover:scale-105 shadow-xl shadow-gray-200"
            >
              {t('hero.cta')}
            </button>
            <button className="w-full sm:w-auto px-8 py-4 bg-white border border-gray-200 text-gray-700 text-lg font-bold rounded-full hover:bg-gray-50 transition-colors">
              {t('hero.learnMembership')}
            </button>
          </div>

          <div className="mt-8 flex items-center justify-center gap-6 text-sm font-medium text-gray-500">
            <div className="flex items-center gap-1.5">
              <FlaskConical size={16} className="text-green-500" />
              {t('badges.scientificFormula')}
            </div>
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={16} className="text-blue-500" />
              {t('badges.privacySecure')}
            </div>
          </div>
        </div>

        {/* Decorative Background Elements */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-white rounded-full blur-3xl opacity-40"></div>
        <div className="absolute top-20 right-0 w-64 h-64 bg-yellow-200 rounded-full blur-3xl opacity-20"></div>
        <div className="absolute bottom-0 left-10 w-48 h-48 bg-blue-100 rounded-full blur-3xl opacity-30"></div>
      </section>

      {/* Features Section */}
      <section id="features-section" className="py-24 bg-white px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">{t('features.sectionTitle')}</h2>
            <p className="text-gray-500 max-w-2xl mx-auto">{t('features.sectionSubtitle')}</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-gray-50 p-8 rounded-3xl border border-gray-100 hover:border-yellow-400 transition-colors group">
              <div className="w-14 h-14 bg-white rounded-2xl shadow-sm flex items-center justify-center text-yellow-500 mb-6 group-hover:scale-110 transition-transform">
                <Brain size={28} />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{t('features.smartAnalysis.title')}</h3>
              <p className="text-gray-600 leading-relaxed">
                {t('features.smartAnalysis.description')}
              </p>
            </div>

            <div className="bg-gray-50 p-8 rounded-3xl border border-gray-100 hover:border-yellow-400 transition-colors group">
              <div className="w-14 h-14 bg-white rounded-2xl shadow-sm flex items-center justify-center text-yellow-500 mb-6 group-hover:scale-110 transition-transform">
                <ListFilter size={28} />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{t('features.priorityRanking.title')}</h3>
              <p className="text-gray-600 leading-relaxed">
                {t('features.priorityRanking.description')}
              </p>
            </div>

            <div className="bg-gray-50 p-8 rounded-3xl border border-gray-100 hover:border-yellow-400 transition-colors group">
              <div className="w-14 h-14 bg-white rounded-2xl shadow-sm flex items-center justify-center text-yellow-500 mb-6 group-hover:scale-110 transition-transform">
                <FileSearch size={28} />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{t('features.transparency.title')}</h3>
              <p className="text-gray-600 leading-relaxed">
                {t('features.transparency.description')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-4 bg-gray-900 text-white text-center">
        <div className="max-w-3xl mx-auto">
          <div className="text-yellow-400 font-bold tracking-widest text-sm mb-4">INTERACTIVE QUIZ</div>
          <h2 className="text-3xl sm:text-4xl font-bold mb-8">{t('cta.sectionTitle')}</h2>
          <p className="text-gray-400 mb-10 text-lg">{t('cta.sectionSubtitle')}</p>
          <button
            onClick={onStartQuiz}
            className="px-8 py-4 bg-yellow-400 text-gray-900 text-lg font-bold rounded-full hover:bg-white transition-all transform hover:scale-105 flex items-center gap-2 mx-auto"
          >
            {t('cta.startButton')} <ArrowRight size={20} />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-50 py-12 border-t border-gray-200">
        <div className="max-w-5xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
              <div className="w-6 h-6 bg-yellow-400 rounded flex items-center justify-center font-bold text-xs text-gray-900">W</div>
              <span className="font-bold text-gray-900">WysikHealth</span>
            </div>
            <p className="text-xs text-gray-500">致力於將複雜的營養科學轉化為簡單、可執行的生活建議。</p>
            <p className="text-xs text-gray-400 mt-2">© 2024 WysikHealth Inc. All rights reserved.</p>
          </div>

          <div className="flex flex-wrap justify-center gap-6 text-sm text-gray-500">
            <a href="#" className="hover:text-gray-900">關於我們</a>
            <a href="#" className="hover:text-gray-900">法律資訊</a>
            <a href="#" className="hover:text-gray-900">隱私權政策</a>
            <a href="#" className="hover:text-gray-900">服務條款</a>
            <a href="#" className="hover:text-gray-900">聯絡我們</a>
          </div>
        </div>
      </footer>
    </div>
  );
};


// Login View Component - 密码登录/注册
const LoginView = ({ onLogin }: { onLogin: () => void }) => {
  const t = useTranslations('auth');
  const tCommon = useTranslations('common');



  // 模式：login (登录) 或 register (注册) 或 admin (管理员登录)
  const [mode, setMode] = useState<'login' | 'register' | 'admin'>('login');
  const [step, setStep] = useState<'input' | 'otp' | 'password'>('input');

  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [termsAgreed, setTermsAgreed] = useState(false);



  // 倒计时效果
  React.useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  // 密码登录
  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || '登入失敗');
      }

      // 保存 token 和用户信息
      if (data.token) {
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('user_id', data.user_id);
        localStorage.setItem('user_email', data.email);
        localStorage.setItem('account_type', data.account_type);
      }

      console.log('✓ Login successful:', data);
      onLogin();
    } catch (err: any) {
      setError(err.message || '登入失敗，請檢查郵箱和密碼');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  // 管理员登录
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || '登入失敗');
      }

      // 保存 token 和用户信息
      if (data.token) {
        // 普通用户登录使用的键
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('user_id', data.username);
        localStorage.setItem('account_type', 'admin');

        // AdminLayout 需要的特定键
        localStorage.setItem('admin_token', data.token);
        localStorage.setItem('admin_username', data.username);
        localStorage.setItem('admin_role', data.role);
      }

      console.log('✓ Admin Login successful:', data);
      onLogin();
    } catch (err: any) {
      setError(err.message || '登入失敗，請檢查用戶名和密碼');
      console.error('Admin Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  // 发送注册 OTP
  const handleSendRegisterOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          purpose: 'register'
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || '發送驗證碼失敗');
      }

      // 单页表单不需要切换步骤，只需启动倒计时
      setCountdown(60);
      console.log('✓ OTP sent successfully');
    } catch (err: any) {
      setError(err.message || '發送驗證碼失敗，請稍後再試');
      console.error('Send OTP error:', err);
    } finally {
      setLoading(false);
    }
  };

  // 验证 OTP 并设置密码（注册流程）
  const handleVerifyAndRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || password.length < 6) {
      setError('密碼至少需要 6 個字符');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          otp_code: otp,
          password,
          consents: {
            terms: true,
            privacy: true,
            health_data: true,
            marketing: false
          }
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || '註冊失敗');
      }

      // 保存 token 和用户信息
      if (data.token) {
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('user_id', data.user_id);
        localStorage.setItem('user_email', data.email);
        localStorage.setItem('account_type', data.account_type);
      }

      console.log('✓ Registration successful:', data);
      onLogin();
    } catch (err: any) {
      setError(err.message || '註冊失敗');
      console.error('Register error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-gray-100">
        <div className="text-center mb-6">
          <div className="w-12 h-12 bg-yellow-400 rounded-xl flex items-center justify-center font-bold text-gray-900 text-2xl mx-auto mb-4">
            W
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            {step === 'otp' ? t('otp.title') : (mode === 'register' ? t('registerTitle') : (mode === 'admin' ? t('adminLoginTitle') : t('loginTitle')))}
          </h2>
          <p className="text-gray-500 mt-2 text-sm">
            {step === 'otp'
              ? t('otp.subtitle', { contact: email })
              : (mode === 'login' ? t('welcomeBack') : t('createAccount'))}
          </p>
        </div>

        {/* 模式切换 Tabs */}
        {step === 'input' && (
          <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
            <button
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'login' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              onClick={() => setMode('login')}
            >
              {tCommon('login')}
            </button>
            <button
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'register' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              onClick={() => setMode('register')}
            >
              {tCommon('register')}
            </button>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        {/* 注册流程：单页表单 - 邮箱、密码、验证码 */}
        {mode === 'register' && (
          <form onSubmit={handleVerifyAndRegister} className="space-y-4">
            {/* 邮箱 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('email')}</label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
                  placeholder={t('emailPlaceholder')}
                  required
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              </div>
            </div>

            {/* 密码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('setPassword')}</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
                  placeholder={t('passwordHint')}
                  minLength={6}
                  required
                />
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* 验证码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('otp.label')}</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-center text-lg tracking-widest font-mono"
                  placeholder={t('otp.placeholder')}
                  maxLength={6}
                  required
                />
                <button
                  type="button"
                  onClick={handleSendRegisterOTP}
                  disabled={loading || !email || countdown > 0}
                  className="px-3 py-2 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap text-xs"
                >
                  {countdown > 0 ? `${countdown}s` : (loading ? t('sending') : t('sendCode'))}
                </button>
              </div>
            </div>

            {/* 服務條款同意勾選 */}
            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                id="termsAgreed"
                checked={termsAgreed}
                onChange={(e) => setTermsAgreed(e.target.checked)}
                className="mt-1 w-4 h-4 text-yellow-400 bg-gray-100 border-gray-300 rounded focus:ring-yellow-400"
              />
              <label htmlFor="termsAgreed" className="text-xs text-gray-600">
                {t('footer.termsAndPrivacy')}
                <a href="/terms" className="text-yellow-600 hover:text-yellow-700 mx-1 underline">{t('footer.termsLink')}</a>
                {t('footer.and')}
                <a href="/privacy" className="text-yellow-600 hover:text-yellow-700 mx-1 underline">{t('footer.privacyLink')}</a>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading || !email || !termsAgreed || otp.length !== 6 || password.length < 6}
              className="w-full bg-gray-900 text-white font-bold py-3.5 rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all shadow-lg shadow-gray-200 disabled:opacity-50 mt-4"
            >
              {loading ? t('registering') : t('completeRegister')}
            </button>
          </form>
        )}

        {/* 登录流程：邮箱 + 密码 */}
        {mode === 'login' && (
          <form onSubmit={handlePasswordLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('email')}</label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
                  placeholder={t('emailPlaceholder')}
                  required
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
                  placeholder={t('passwordPlaceholder')}
                  required
                />
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <div className="text-right mt-1">
                <button type="button" className="text-xs text-gray-500 hover:text-yellow-600">{t('forgotPassword')}</button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full bg-gray-900 text-white font-bold py-3.5 rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all shadow-lg shadow-gray-200 disabled:opacity-50 mt-4"
            >
              {loading ? t('loggingIn') : tCommon('login')}
            </button>
          </form>
        )}

        {/* 管理员登录流程：用户名 + 密码 */}
        {mode === 'admin' && (
          <form onSubmit={handleAdminLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('username')}</label>
              <div className="relative">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
                  placeholder="admin"
                  required
                />
                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
                  placeholder={t('passwordPlaceholder')}
                  required
                />
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full bg-gray-900 text-white font-bold py-3.5 rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all shadow-lg shadow-gray-200 disabled:opacity-50 mt-4"
            >
              {loading ? t('loggingIn') : tCommon('login')}
            </button>
          </form>
        )}


        <div className="mt-4 text-center">
          {mode === 'login' ? (
            <button
              type="button"
              onClick={() => setMode('admin')}
              className="text-xs text-gray-400 hover:text-gray-600 underline"
            >
              {t('isAdminPartner')}
            </button>
          ) : mode === 'admin' ? (
            <button
              type="button"
              onClick={() => setMode('login')}
              className="text-xs text-gray-400 hover:text-gray-600 underline"
            >
              {t('backToUserLogin')}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
};

// File Upload Component
const FileUpload = ({ onFileSelect }: { onFileSelect: (files: File[]) => void }) => {
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const t = useTranslations('quiz');

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
    // 重置 input 值，确保连续拍照/选同一文件时仍能触发 onChange
    e.target.value = '';
  };

  const handleFiles = (newFiles: FileList) => {
    const validFiles = Array.from(newFiles).filter(file => {
      const isValidType = ['application/pdf', 'image/jpeg', 'image/png'].includes(file.type);
      const isValidSize = file.size <= 50 * 1024 * 1024;
      return isValidType && isValidSize;
    });
    setFiles([...files, ...validFiles]);
    onFileSelect([...files, ...validFiles]);
  };

  const removeFile = (idx: number) => {
    const newFiles = files.filter((_, i) => i !== idx);
    setFiles(newFiles);
    onFileSelect(newFiles);
  };

  return (
    <div className="mt-8">
      <h3 className="text-lg font-bold text-gray-900 mb-2">{t('upload.title')}</h3>
      <p className="text-sm text-gray-500 mb-4">
        {t('upload.description')}
      </p>

      <div
        className={`relative border-2 border-dashed rounded-xl p-8 transition-all text-center
          ${dragActive ? 'border-yellow-400 bg-yellow-50' : 'border-gray-300 bg-gray-50 hover:bg-white'}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {/* 文件选择 input */}
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleChange}
        />
        {/* 拍照专用 input（移动端调起摄像头） */}
        <input
          id="camera-input"
          type="file"
          accept="image/jpeg,image/png"
          capture="environment"
          className="hidden"
          onChange={handleChange}
        />

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8">
          {/* 文件上传区域 */}
          <div className="flex flex-col items-center gap-2 cursor-pointer" onClick={() => inputRef.current?.click()}>
            <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center text-gray-400 hover:text-yellow-500 transition-colors">
              <Upload size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {t('upload.dragDrop')} <span className="text-yellow-600 hover:underline">{t('upload.clickUpload')}</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG (Max 50MB)</p>
            </div>
          </div>

          {/* 分隔线 */}
          <div className="hidden sm:flex flex-col items-center gap-1">
            <div className="w-px h-8 bg-gray-200"></div>
            <span className="text-xs text-gray-400">{t('upload.orDivider')}</span>
            <div className="w-px h-8 bg-gray-200"></div>
          </div>
          <div className="flex sm:hidden items-center gap-3 w-full max-w-[200px]">
            <div className="flex-1 h-px bg-gray-200"></div>
            <span className="text-xs text-gray-400">{t('upload.orDivider')}</span>
            <div className="flex-1 h-px bg-gray-200"></div>
          </div>

          {/* 拍照按钮 */}
          <div
            className="flex flex-col items-center gap-2 cursor-pointer"
            onClick={() => document.getElementById('camera-input')?.click()}
          >
            <div className="w-12 h-12 bg-gradient-to-br from-yellow-400 to-orange-400 rounded-full shadow-md flex items-center justify-center text-white hover:shadow-lg hover:scale-105 transition-all">
              <Camera size={24} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-gray-900">{t('upload.cameraUpload')}</p>
              <p className="text-xs text-gray-400 mt-1">{t('upload.cameraDesc')}</p>
            </div>
          </div>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((file, idx) => (
            <div key={idx} className="flex items-center justify-between bg-white border border-gray-200 p-3 rounded-lg">
              <div className="flex items-center gap-3 overflow-hidden">
                <FileText size={18} className="text-yellow-500 flex-shrink-0" />
                <span className="text-sm text-gray-700 truncate">{file.name}</span>
                <span className="text-xs text-gray-400">({(file.size / 1024 / 1024).toFixed(1)} MB)</span>
              </div>
              <button
                onClick={() => removeFile(idx)}
                className="text-gray-400 hover:text-red-500 p-1"
              >
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


// Product Carousel - 使用 AI 推荐的商品
const ProductCarousel = ({ products, whyReasons }: {
  products: ProductRecommendation[];
  whyReasons?: string[];
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const tResults = useTranslations('results');

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 240;
      if (direction === 'left') {
        scrollRef.current.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
      } else {
        scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
      }
    }
  };

  // 获取图片 URL（处理相对路径）
  const getImageSrc = (imageUrl?: string) => {
    if (!imageUrl) return 'https://placehold.co/360x360/e0e0e0/555?text=Product';
    if (imageUrl.startsWith('http')) return imageUrl;
    if (imageUrl.startsWith('/api/')) return `http://localhost:8000${imageUrl}`;
    return imageUrl;
  };

  if (!products || products.length === 0) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-500 text-center border border-dashed border-gray-200">
        {tResults('noProducts')}
      </div>
    );
  }

  return (
    <div className="mt-4 relative group">
      {products.length > 2 && (
        <>
          <button
            onClick={() => scroll('left')}
            className="absolute -left-3 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-white border border-gray-200 rounded-full shadow-md flex items-center justify-center text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-50"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={() => scroll('right')}
            className="absolute -right-3 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-white border border-gray-200 rounded-full shadow-md flex items-center justify-center text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-50"
          >
            <ChevronRight size={18} />
          </button>
        </>
      )}

      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto pb-4 snap-x"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {products.map((product, idx) => (
          <div
            key={product.product_id}
            className="flex-shrink-0 w-[200px] sm:w-[260px] bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow snap-start flex flex-col"
          >
            <div className="relative">
              <img
                src={getImageSrc(product.image_url)}
                alt={product.product_name}
                className="w-full h-36 object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = 'https://placehold.co/360x360/e0e0e0/555?text=Product';
                }}
              />
              {idx === 0 && (
                <span className="absolute top-2 left-2 bg-yellow-400 text-xs font-bold px-2 py-0.5 rounded text-gray-900">
                  {tResults('aiRecommended')}
                </span>
              )}
              {product.partner_name && (
                <span className="absolute top-2 right-2 bg-white/90 text-xs px-2 py-0.5 rounded text-gray-600">
                  {product.partner_name}
                </span>
              )}
            </div>

            <div className="p-3 flex flex-col flex-1">
              <h4 className="text-sm font-bold text-gray-900 line-clamp-2 min-h-[2.5rem]">
                {product.product_name}
              </h4>

              {/* AI 推荐理由 */}
              {product.why_this_product && product.why_this_product.length > 0 && (
                <div className="mt-2 text-xs text-gray-500 space-y-1">
                  {product.why_this_product.slice(0, 2).map((reason, i) => (
                    <div key={i} className="flex items-start gap-1">
                      <CheckCircle size={12} className="text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="line-clamp-2">{reason}</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-auto pt-2 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600">
                  {product.price ? `${product.currency} ${product.price}` : '價格洽詢'}
                </span>
                <button className="bg-gray-900 text-white p-1.5 rounded-full hover:bg-yellow-500 hover:text-gray-900 transition-colors">
                  <ShoppingCart size={16} />
                </button>
              </div>
              <a
                href={product.purchase_url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full mt-3 text-xs font-bold border border-gray-900 text-gray-900 py-1.5 rounded-full hover:bg-gray-900 hover:text-white transition-colors text-center block"
              >
                {tResults('product.buy')}
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/* =========================================
   3. Main Application Logic
   ========================================= */

interface QuizResult {
  screenScore: number;
  detailScore: number;
  totalScore: number;
}

export default function App() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [view, setView] = useState<'landing' | 'login' | 'quiz' | 'upload' | 'loading' | 'result'>('landing');
  const [currentSuppIndex, setCurrentSuppIndex] = useState(0);
  const [phase, setPhase] = useState<'screen' | 'detail'>('screen');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [results, setResults] = useState<Record<string, QuizResult>>({});
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  // 报告相关状态
  const [reportId, setReportId] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState<'idle' | 'uploading' | 'processing' | 'completed' | 'failed'>('idle');
  const [extractedHealthData, setExtractedHealthData] = useState<any>(null);

  // AI 推荐结果状态
  const [aiRecommendations, setAiRecommendations] = useState<AIRecommendationResponse | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  // 使用量状态
  const [usageInfo, setUsageInfo] = useState<{
    used: number;
    remaining: number;
    limit: number;
    reset_at: string;
  } | null>(null);

  const handleLogin = () => {
    // 检查是否为管理员登录
    // 检查是否为管理员登录
    const accountType = typeof window !== 'undefined' ? localStorage.getItem('account_type') : null;
    if (accountType === 'admin') {
      router.push('/admin/dashboard');
      return;
    }

    setIsLoggedIn(true);
    setView('quiz');

    // 获取使用量信息
    const locale = typeof window !== 'undefined' ? (localStorage.getItem('NEXT_LOCALE') || 'zh-TW') : 'zh-TW';
    const userId = typeof window !== 'undefined' ? (localStorage.getItem('user_id') || '') : '';
    fetch(`${API_BASE_URL}/api/quiz/usage`, {
      headers: {
        'Accept-Language': locale,
        'X-User-ID': userId
      }
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setUsageInfo(data.data);
        }
      })
      .catch(error => {
        console.error('Failed to fetch usage info:', error);
      });
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    resetQuiz();
    setView('landing');
  };

  const currentSupp = supplementsConfig[currentSuppIndex];
  const currentList = currentSupp
    ? (phase === 'screen' ? currentSupp.screening : currentSupp.detail)
    : [];
  const currentQuestion = currentList[questionIndex];

  const handleAnswer = (score: number) => {
    setResults(prev => {
      const suppId = currentSupp.id;
      const prevRes = prev[suppId] || { screenScore: 0, detailScore: 0, totalScore: 0 };
      const newRes = { ...prevRes };
      if (phase === 'screen') {
        newRes.screenScore += score;
      } else {
        newRes.detailScore += score;
      }
      return { ...prev, [suppId]: newRes };
    });

    const isLastQuestionInPhase = questionIndex >= currentList.length - 1;

    if (!isLastQuestionInPhase) {
      setQuestionIndex(prev => prev + 1);
    } else {
      if (phase === 'screen') {
        const currentScore = (results[currentSupp.id]?.screenScore || 0) + score;
        const threshold = currentSupp.screeningThreshold || 2;

        if (currentSupp.detail && currentSupp.detail.length > 0 && currentScore >= threshold) {
          setPhase('detail');
          setQuestionIndex(0);
        } else {
          finishSupplement();
        }
      } else {
        finishSupplement();
      }
    }
  };

  const finishSupplement = () => {
    const nextIndex = currentSuppIndex + 1;
    if (nextIndex < supplementsConfig.length) {
      setCurrentSuppIndex(nextIndex);
      setPhase('screen');
      setQuestionIndex(0);
    } else {
      setView('upload');
    }
  };

  const handleUploadComplete = async () => {
    console.log('[handleUploadComplete] called, uploadedFiles:', uploadedFiles);
    console.log('[handleUploadComplete] uploadedFiles.length:', uploadedFiles.length);
    if (uploadedFiles.length > 0) {
      console.log('[handleUploadComplete] File 0:', uploadedFiles[0].name, uploadedFiles[0].type, uploadedFiles[0].size);
    }
    setView('loading');
    setLoadingError(null);

    const locale = typeof window !== 'undefined' ? (localStorage.getItem('NEXT_LOCALE') || 'zh-TW') : 'zh-TW';

    // 使用局部变量保存健康数据，避免 React 状态异步更新问题
    let localHealthData: any = null;

    // 1. 如果有上传文件，先处理文件上传
    if (uploadedFiles.length > 0) {
      try {
        setReportStatus('uploading');

        // 只上传第一个文件
        const file = uploadedFiles[0];
        const formData = new FormData();
        formData.append('file', file);

        const uploadResponse = await fetch(`${API_BASE_URL}/api/report/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!uploadResponse.ok) {
          throw new Error('文件上传失败');
        }

        const uploadData = await uploadResponse.json();
        setReportId(uploadData.report_id);
        setReportStatus('processing');

        // 轮询检查报告处理状态
        let attempts = 0;
        const maxAttempts = 30; // 最多等待30秒

        while (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1000));

          const statusResponse = await fetch(`${API_BASE_URL}/api/report/status/${uploadData.report_id}`);
          console.log(`[Report] Polling attempt ${attempts + 1}, status response ok: ${statusResponse.ok}`);

          if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            console.log(`[Report] Status: ${statusData.status}, extracted_data:`, statusData.extracted_data);

            if (statusData.status === 'completed') {
              console.log('[Report] Extraction completed, setting extracted health data');
              localHealthData = statusData.extracted_data; // 保存到局部变量
              setExtractedHealthData(statusData.extracted_data);
              setReportStatus('completed');
              break;
            } else if (statusData.status === 'failed') {
              setReportStatus('failed');
              console.error('Report extraction failed:', statusData.error);
              break;
            }
          }

          attempts++;
        }

        if (attempts >= maxAttempts) {
          setReportStatus('failed');
          console.warn('Report processing timeout');
        }

      } catch (error) {
        console.error('Failed to upload report:', error);
        setReportStatus('failed');
        // 继续执行，不阻止问卷提交
      }
    }

    // 2. 获取使用量信息
    // 获取用户 ID 用于使用量追踪
    const userId = typeof window !== 'undefined' ? localStorage.getItem('user_id') || '' : '';

    try {
      const usageResponse = await fetch(`${API_BASE_URL}/api/quiz/usage`, {
        headers: {
          'Accept-Language': locale,
          'X-User-ID': userId
        }
      });
      if (usageResponse.ok) {
        const usageData = await usageResponse.json();
        setUsageInfo(usageData.data);
      }
    } catch (error) {
      console.error('Failed to fetch usage info:', error);
    }

    // 3. 提交问卷并获取 AI 推荐
    try {
      // 构建所有答案数据
      const allAnswers = supplementsConfig.map(supp => {
        const r = results[supp.id] || { screenScore: 0, detailScore: 0, totalScore: 0 };
        const total = (r.screenScore || 0) + (r.detailScore || 0);
        let level: 'high' | 'medium' | 'low' | 'none' = 'none';
        if (total >= 6) level = 'high';
        else if (total >= 3) level = 'medium';
        else if (total >= 1) level = 'low';

        return {
          supplement_id: supp.id,
          supplement_name: supp.name,
          group: supp.group,
          screen_score: r.screenScore || 0,
          detail_score: r.detailScore || 0,
          total_score: total,
          level: level
        };
      });

      // 获取前3个高分结果
      const topResults = [...allAnswers]
        .filter(a => a.level === 'high' || a.level === 'medium')
        .sort((a, b) => b.total_score - a.total_score)
        .slice(0, 3);

      // 优先使用局部变量（刚提取的数据），否则使用状态变量
      const healthDataToSubmit = localHealthData || extractedHealthData;

      console.log('Submitting quiz to AI API...', { allAnswers, topResults });
      console.log('Health data to submit:', healthDataToSubmit);
      console.log('Health data keys:', healthDataToSubmit ? Object.keys(healthDataToSubmit) : 'null');

      // 调用后端 AI API
      const response = await fetch(`${API_BASE_URL}/api/quiz/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept-Language': locale,
          'X-User-ID': userId
        },
        body: JSON.stringify({
          answers: allAnswers,
          top_results: topResults.length > 0 ? topResults : allAnswers.slice(0, 3),
          health_data: healthDataToSubmit // 使用局部变量或状态变量
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        const errorMessage = errorData.detail || `API error: ${response.status}`;

        if (response.status === 429) {
          // API 并发限制或每日限制
          throw new Error(errorMessage);
        } else if (response.status === 503) {
          // AI 服务不可用
          throw new Error(errorMessage);
        } else if (response.status === 504) {
          // 超时
          throw new Error(errorMessage);
        } else {
          throw new Error(errorMessage);
        }
      }

      const data: AIRecommendationResponse = await response.json();
      console.log('AI Recommendations received:', data);

      setAiRecommendations(data);
      setView('result');

    } catch (error) {
      console.error('Failed to get AI recommendations:', error);
      const errorMessage = error instanceof Error ? error.message : '獲取 AI 推薦失敗';
      setLoadingError(errorMessage);
      // 显示错误后返回问卷页面
      alert(`❌ ${errorMessage}\n\n請稍後再試。`);
      setView('upload');
      // 即使失败也显示结果页面（使用本地计算的结果）
      setView('result');
    }
  };

  const calculateFinalResults = () => {
    const processedResults = Object.keys(results).map(key => {
      const r = results[key];
      const total = (r.screenScore || 0) + (r.detailScore || 0);
      let level: 'high' | 'medium' | 'none' = 'none';
      if (total >= 6) level = 'high';
      else if (total >= 3) level = 'medium';

      return {
        id: key,
        ...r,
        totalScore: total,
        level,
        suppConfig: supplementsConfig.find(s => s.id === key)!
      };
    });

    const recommendations = processedResults
      .filter(r => r.level === 'high' || r.level === 'medium')
      .sort((a, b) => b.totalScore - a.totalScore)
      .slice(0, 5);

    return recommendations;
  };

  const resetQuiz = () => {
    setView('quiz');
    setCurrentSuppIndex(0);
    setPhase('screen');
    setQuestionIndex(0);
    setResults({});
    setUploadedFiles([]);
    setAiRecommendations(null);
    setLoadingError(null);
    // 重置化验报告相关状态
    setExtractedHealthData(null);
    setReportId(null);
    setReportStatus('idle');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // 重新获取使用量信息
    const locale = typeof window !== 'undefined' ? (localStorage.getItem('NEXT_LOCALE') || 'zh-TW') : 'zh-TW';
    const userId = typeof window !== 'undefined' ? (localStorage.getItem('user_id') || '') : '';
    fetch(`${API_BASE_URL}/api/quiz/usage`, {
      headers: {
        'Accept-Language': locale,
        'X-User-ID': userId
      }
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setUsageInfo(data.data);
        }
      })
      .catch(error => {
        console.error('Failed to fetch usage info:', error);
      });
  };


  // 1. Landing Page
  if (view === 'landing') {
    return (
      <>
        <Header
          onRestart={() => setView('landing')}
          isLoggedIn={false}
          onLoginClick={() => setView('login')}
          view="landing"
        />
        <LandingPage onStartQuiz={() => setView('login')} />
      </>
    );
  }

  // 2. Login Page
  if (view === 'login') {
    return (
      <div className="min-h-screen bg-[#f5f5f7] font-sans text-gray-900">
        <Header
          onRestart={() => setView('landing')}
          isLoggedIn={false}
          onLoginClick={() => setView('login')}
          view="login"
        />
        <LoginView onLogin={handleLogin} />
      </div>
    );
  }

  // 3. Loading State
  if (view === 'loading') {
    return <LoadingView usageInfo={usageInfo} onLogout={handleLogout} />;
  }

  // 4. Result State
  if (view === 'result') {
    return <ResultView
      aiRecommendations={aiRecommendations}
      loadingError={loadingError}
      extractedHealthData={extractedHealthData}
      calculateFinalResults={calculateFinalResults}
      resetQuiz={resetQuiz}
      onLogout={handleLogout}
    />;
  }

  // 5. Quiz / Upload View
  return <QuizUploadView
    view={view}
    currentSuppIndex={currentSuppIndex}
    currentSupp={currentSupp}
    currentQuestion={currentQuestion}
    phase={phase}
    questionIndex={questionIndex}
    results={results}
    uploadedFiles={uploadedFiles}
    usageInfo={usageInfo}
    onAnswer={handleAnswer}
    onUploadComplete={handleUploadComplete}
    onRestart={() => setView('landing')}
    onLogout={handleLogout}
    setUploadedFiles={setUploadedFiles}
  />;
}

// Loading View 子组件
function LoadingView({ usageInfo, onLogout }: any) {
  const t = useTranslations('quiz');
  const tResults = useTranslations('results');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header onRestart={() => { }} isLoggedIn={true} onLogout={onLogout} />
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 border-4 border-gray-200 border-t-yellow-400 rounded-full animate-spin mb-6"></div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('analyzing')}</h2>
        <p className="text-gray-500 max-w-md">
          {t('pleaseWait')}
        </p>

        {/* 显示剩余次数 */}
        {usageInfo && (
          <div className="mt-8 p-4 bg-white border border-gray-200 rounded-xl shadow-sm max-w-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">{t('usage.todayAnalysis')}</span>
              <span className="text-xs text-gray-400">
                {new Date(usageInfo.reset_at).toLocaleDateString('zh-TW')}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-gray-900">{usageInfo.remaining}</span>
              <span className="text-sm text-gray-500">
                {tResults('usageRemaining', { remaining: usageInfo.remaining })}
              </span>
            </div>
            <div className="mt-2 w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-yellow-400 h-full transition-all duration-300"
                style={{ width: `${(usageInfo.remaining / usageInfo.limit) * 100}%` }}
              ></div>
            </div>
            {usageInfo.remaining === 0 && (
              <p className="mt-2 text-xs text-red-600">
                {tResults('usageLimit', { limit: usageInfo.limit })}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Result View 子组件
function ResultView({
  aiRecommendations,
  loadingError,
  extractedHealthData,
  calculateFinalResults,
  resetQuiz,
  onLogout
}: any) {
  const tResults = useTranslations('results');

  // 优先使用 AI 推荐结果
  const hasAiResults = aiRecommendations && aiRecommendations.items && aiRecommendations.items.length > 0;
  const finalRecs = hasAiResults ? null : calculateFinalResults();

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <Header onRestart={resetQuiz} isLoggedIn={true} onLogout={onLogout} />

      <div className="sq-container">
        {/* 进度条 - 100% */}
        <div className="sq-progress">
          <div className="sq-bar" style={{ width: '100%' }}></div>
        </div>

        {/* 状态列 */}
        <div className="sq-status">
          <span className="sq-current-supp">{tResults('analysisComplete')}</span>
          <span style={{ marginLeft: '8px' }}>
            {hasAiResults
              ? tResults('aiGenerated')
              : tResults('localCalculated')
            }
          </span>
          {/* 显示是否基于体检报告 */}
          {aiRecommendations?.based_on_lab_report && (
            <span style={{
              marginLeft: '8px',
              background: '#DBEAFE',
              color: '#1E40AF',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600'
            }}>
              🩺 基於體檢報告
            </span>
          )}
        </div>

        {loadingError && (
          <div className="sq-report-badge" style={{ background: '#FEF3C7', color: '#92400E', marginBottom: '16px' }}>
            ⚠️ {loadingError}（{tResults('usingLocalResults')}）
          </div>
        )}

        {/* 结果区域 */}
        <div id="sq-result-area">
          {/* 化验值展示 */}
          {extractedHealthData && (
            <HealthDataDisplay data={extractedHealthData} />
          )}

          {hasAiResults ? (
            // 显示 AI 推荐结果
            aiRecommendations!.items.map((rec: any, idx: number) => (
              <div key={rec.supplement_id} className="sq-result-card">
                <div className="sq-report-badge">{tResults('assessmentResult')}：{rec.group}</div>
                <h3 className="sq-result-title">{tResults('recommendedDirection')}：{rec.name}</h3>

                {/* AI 推荐原因 */}
                <div className="sq-medical-note">
                  <strong>{tResults('aiReasons')}</strong><br />
                  {rec.why.map((reason: string, i: number) => (
                    <span key={i}>• {reason}<br /></span>
                  ))}
                </div>

                {/* 安全提示 */}
                {rec.safety && rec.safety.length > 0 && (
                  <div className="sq-medical-note" style={{ borderLeftColor: '#F59E0B' }}>
                    <strong>⚠️ {tResults('safetyWarning')}：</strong><br />
                    {rec.safety.map((warning: string, i: number) => (
                      <span key={i}>• {warning}<br /></span>
                    ))}
                  </div>
                )}

                <div className="sq-result-tag">
                  {tResults('confidenceScore', { score: rec.confidence })}
                </div>

                {/* AI 推荐的商品 */}
                {rec.recommended_products && rec.recommended_products.length > 0 ? (
                  <>
                    <div className="sq-product-section-title">
                      🛒 {tResults('aiRecommendedProducts')}
                    </div>
                    <div className="sq-product-list">
                      {rec.recommended_products.map((product: any) => (
                        <div key={product.product_id} className="sq-product-card">
                          {/* 收藏按钮 */}
                          <FavoriteButton productId={product.product_id} />

                          {/* Sponsored 标签 */}
                          {product.partner_name && (
                            <div style={{
                              position: 'absolute',
                              top: '8px',
                              right: '8px',
                              background: 'rgba(251, 191, 36, 0.9)',
                              color: '#78350f',
                              padding: '4px 12px',
                              borderRadius: '12px',
                              fontSize: '11px',
                              fontWeight: '600',
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                            }}>
                              ⭐ Sponsored
                            </div>
                          )}

                          <img
                            src={product.image_url?.startsWith('/api/')
                              ? `http://localhost:8000${product.image_url}`
                              : product.image_url || 'https://placehold.co/360x360/e0e0e0/555?text=Product'
                            }
                            alt={product.product_name}
                            className="sq-product-img"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = 'https://placehold.co/360x360/e0e0e0/555?text=Product';
                            }}
                          />
                          <div className="sq-product-title">{product.product_name}</div>

                          {/* 合作商名称 */}
                          {product.partner_name && (
                            <div className="sq-product-partner">
                              by {product.partner_name}
                            </div>
                          )}

                          <div className="sq-product-price">
                            {product.price ? `${product.currency} ${product.price}` : '價格洽詢'}
                          </div>

                          {/* AI 推荐理由 - 黄色高亮 */}
                          {product.why_this_product && product.why_this_product.length > 0 && (
                            <div className="sq-ai-reasons">
                              <div className="sq-ai-reasons-title">✨ {tResults('aiReasons')}</div>
                              <ul className="sq-ai-reasons-list">
                                {product.why_this_product.map((reason: string, i: number) => (
                                  <li key={i}>→ {reason}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <a
                            href={product.purchase_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="sq-buy-btn"
                            onClick={async (e) => {
                              // 追踪产品点击事件
                              try {
                                const token = localStorage.getItem('access_token');
                                await fetch(`${API_BASE_URL}/api/analytics/events/product-clicked`, {
                                  method: 'POST',
                                  headers: {
                                    'Content-Type': 'application/json',
                                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                                  },
                                  body: JSON.stringify({
                                    product_id: product.product_id,
                                    session_id: aiRecommendations?.session_id,
                                    recommendation_item_id: rec.supplement_id,
                                    redirect_url: product.purchase_url
                                  })
                                });
                              } catch (error) {
                                console.error('Failed to track product click:', error);
                              }
                            }}
                          >
                            {tResults('product.buy')}
                          </a>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="sq-product-empty">{tResults('noProducts')}</div>
                )}
              </div>
            ))
          ) : finalRecs && finalRecs.length > 0 ? (
            // 显示本地计算的结果（回退方案）
            finalRecs.map((rec: any) => (
              <div key={rec.id} className="sq-result-card">
                <div className="sq-report-badge">{tResults('assessmentResult')}：{rec.suppConfig.group}</div>
                <h3 className="sq-result-title">{tResults('recommendedDirection')}：{rec.suppConfig.name}</h3>

                <div className="sq-medical-note">
                  <strong>{tResults('description')}：</strong><br />
                  {rec.suppConfig.note}
                </div>

                <div className="sq-result-tag">
                  {tResults('priority')}：{rec.level === 'high' ? tResults('highPriority') : tResults('mediumPriority')}（{tResults('internalScore')}：{rec.totalScore}）
                </div>

                <div className="sq-product-empty">{tResults('noProducts')}</div>
              </div>
            ))
          ) : (
            <div className="sq-result-card">
              <div className="sq-report-badge">{tResults('noRecommendations')}</div>
              <h3 className="sq-result-title">{tResults('focusOnLifestyle')}</h3>
              <div className="sq-medical-note">
                <strong>{tResults('description')}：</strong><br />
                {tResults('noRecommendationsDetail')}
              </div>
            </div>
          )}

          {/* 免责声明 */}
          <div className="sq-disclaimer">
            {aiRecommendations?.disclaimer || tResults('disclaimer')}
          </div>

          {/* 重新测评按钮 */}
          <div className="sq-result-actions" style={{ marginTop: '24px', textAlign: 'center' }}>
            <button
              type="button"
              className="sq-restart-btn"
              onClick={resetQuiz}
            >
              {tResults('retakeQuiz')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Quiz/Upload View 子组件
function QuizUploadView({
  view,
  currentSuppIndex,
  currentSupp,
  currentQuestion,
  phase,
  questionIndex,
  results,
  uploadedFiles,
  usageInfo,
  onAnswer,
  onUploadComplete,
  onRestart,
  onLogout,
  setUploadedFiles
}: any) {
  const t = useTranslations('quiz');
  const tResults = useTranslations('results');

  const totalSteps = supplementsConfig.length + 1;
  const currentStep = view === 'upload' ? totalSteps : currentSuppIndex + 1;
  const progressPercent = (currentStep / totalSteps) * 100;

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <Header onRestart={onRestart} isLoggedIn={true} onLogout={onLogout} />

      <div className="sq-container">
        {/* 进度条 */}
        <div className="sq-progress">
          <div
            className="sq-bar"
            style={{ width: `${progressPercent}%` }}
          ></div>
        </div>

        {/* 显示剩余次数 */}
        {usageInfo && (
          <div className="mb-4 p-3 bg-white border border-gray-200 rounded-lg shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain size={18} className="text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">
                {t('usage.todayRemaining')}：
              </span>
              <span className="text-sm font-bold text-gray-900">
                {usageInfo.remaining} / {usageInfo.limit}
              </span>
            </div>
            {usageInfo.remaining === 0 && (
              <span className="text-xs text-red-600 font-medium">
                {tResults('usageLimit', { limit: usageInfo.limit })}
              </span>
            )}
          </div>
        )}

        {view === 'upload' ? (
          <div className="sq-question-area">
            <div className="text-center mb-6">
              <h2 className="sq-result-title">最後一步</h2>
              <p className="sq-status">上傳報告以獲得更精準的分析，或直接開始計算。</p>
            </div>

            <FileUpload onFileSelect={setUploadedFiles} />

            <button
              onClick={onUploadComplete}
              className="sq-restart-btn w-full mt-8"
            >
              {t('startAnalysis')}
            </button>
            <button
              onClick={onUploadComplete}
              className="w-full mt-3 text-gray-400 text-sm hover:text-gray-600"
            >
              {t('skip')}
            </button>
          </div>
        ) : currentQuestion ? (
          <div className="sq-question-area" key={`${currentSuppIndex}-${phase}-${questionIndex}`}>
            {/* 状态列 */}
            <div className="sq-status">
              <div className="sq-current-supp">
                目前營養線：{currentSupp.name}
              </div>
              <div>
                {t('progress', { current: currentSuppIndex + 1, total: supplementsConfig.length })}｜階段：{phase === 'screen' ? '初步篩檢' : '詳細評估'}
              </div>
            </div>

            {/* 问题 */}
            <div className="sq-question-title">
              {currentQuestion.subtitle}
            </div>
            <div className="sq-question-text">
              {currentQuestion.text}
            </div>

            {/* 选项 */}
            <div className="sq-options">
              {currentQuestion.options.map((opt: { label: string; score: number }, i: number) => (
                <button
                  key={i}
                  onClick={() => onAnswer(opt.score)}
                  className="sq-option-btn"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
