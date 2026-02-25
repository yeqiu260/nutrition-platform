'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';

export default function PrivacyPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft size={20} />
            <span>返回</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="bg-white rounded-xl shadow-sm p-8 md:p-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">隱私條款</h1>
          <p className="text-sm text-gray-500 mb-8">最後更新日期：2024年1月20日</p>

          <div className="prose prose-gray max-w-none space-y-6">
            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">1. 引言</h2>
              <p className="text-gray-700 leading-relaxed">
                WysikHealth（以下簡稱「我們」或「本平台」）非常重視您的隱私保護。本隱私條款說明我們如何收集、使用、存儲和保護您的個人資訊。使用本平台服務即表示您同意本隱私條款的內容。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">2. 我們收集的資訊</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                我們可能收集以下類型的資訊：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li><strong>帳戶資訊：</strong>電子郵件地址、手機號碼</li>
                <li><strong>問卷資訊：</strong>生活型態、飲食習慣、睡眠狀況、運動頻率等</li>
                <li><strong>健康數據：</strong>您上傳的體檢報告中的數值（如血液檢查結果）</li>
                <li><strong>使用資訊：</strong>瀏覽記錄、點擊行為、設備資訊、IP地址</li>
                <li><strong>偏好設定：</strong>語言選擇、收藏的產品</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">3. 資訊使用目的</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                我們收集和使用您的資訊用於以下目的：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>提供個性化的營養補充品推薦服務</li>
                <li>改進和優化我們的AI算法和服務質量</li>
                <li>發送服務相關通知和更新</li>
                <li>回應您的查詢和提供客戶支持</li>
                <li>進行數據分析和研究（僅使用去識別化數據）</li>
                <li>遵守法律法規要求</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">4. 資訊保護措施</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                我們採取以下措施保護您的個人資訊：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li><strong>加密存儲：</strong>所有敏感數據使用AES-256加密算法存儲</li>
                <li><strong>傳輸加密：</strong>使用HTTPS/TLS協議保護數據傳輸</li>
                <li><strong>訪問控制：</strong>嚴格限制員工訪問個人資訊的權限</li>
                <li><strong>安全審計：</strong>定期進行安全審計和漏洞掃描</li>
                <li><strong>病毒掃描：</strong>上傳的文件會進行病毒掃描</li>
                <li><strong>防提示詞注入：</strong>AI系統具備防惡意輸入保護機制</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">5. 資訊共享與披露</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                我們不會出售您的個人資訊。我們僅在以下情況下共享您的資訊：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li><strong>經您同意：</strong>在獲得您明確同意的情況下</li>
                <li><strong>服務提供商：</strong>與協助我們提供服務的第三方（如雲端服務提供商），但他們僅能按照我們的指示使用資訊</li>
                <li><strong>商業合作夥伴：</strong>推薦產品的合作夥伴（僅共享必要的匿名化數據）</li>
                <li><strong>法律要求：</strong>根據法律法規、法院命令或政府要求</li>
                <li><strong>保護權益：</strong>為保護我們或他人的合法權益</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">6. Cookie 和追蹤技術</h2>
              <p className="text-gray-700 leading-relaxed">
                我們使用Cookie和類似技術來改善用戶體驗、分析網站使用情況和提供個性化內容。您可以通過瀏覽器設置管理Cookie偏好，但這可能影響某些功能的使用。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">7. 您的權利</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                您對自己的個人資訊享有以下權利：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li><strong>訪問權：</strong>查看我們持有的您的個人資訊</li>
                <li><strong>更正權：</strong>要求更正不準確的資訊</li>
                <li><strong>刪除權：</strong>要求刪除您的個人資訊</li>
                <li><strong>限制處理權：</strong>要求限制對您資訊的處理</li>
                <li><strong>數據可攜權：</strong>以結構化、常用格式獲取您的資訊</li>
                <li><strong>反對權：</strong>反對我們處理您的資訊</li>
                <li><strong>撤回同意權：</strong>隨時撤回您的同意</li>
              </ul>
              <p className="text-gray-700 leading-relaxed mt-3">
                如需行使這些權利，請通過本頁面底部的聯繫方式與我們聯繫。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">8. 資訊保留期限</h2>
              <p className="text-gray-700 leading-relaxed">
                我們僅在必要期限內保留您的個人資訊。一般而言，帳戶資訊在帳戶存續期間保留；問卷和推薦記錄保留2年；去識別化的研究數據可能長期保留。您可以隨時要求刪除您的資訊。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">9. 兒童隱私</h2>
              <p className="text-gray-700 leading-relaxed">
                本平台不針對18歲以下的兒童。我們不會故意收集兒童的個人資訊。如果您發現我們收集了兒童的資訊，請立即聯繫我們，我們將盡快刪除。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">10. 跨境數據傳輸</h2>
              <p className="text-gray-700 leading-relaxed">
                您的資訊可能被傳輸到您所在國家/地區以外的地方進行處理和存儲。我們會確保這些傳輸符合適用的數據保護法律，並採取適當的保護措施。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">11. 隱私條款更新</h2>
              <p className="text-gray-700 leading-relaxed">
                我們可能不時更新本隱私條款。重大變更時，我們會通過電子郵件或網站公告通知您。更新後的條款將在本頁面公布，並註明生效日期。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">12. 聯繫我們</h2>
              <p className="text-gray-700 leading-relaxed">
                如您對本隱私條款有任何疑問、意見或投訴，或希望行使您的權利，請通過以下方式聯繫我們：
              </p>
              <p className="text-gray-700 mt-2">
                電子郵件：privacy@wysikhealth.com<br />
                客服時間：週一至週五 9:00-18:00<br />
                回應時間：我們將在收到請求後30天內回應
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
