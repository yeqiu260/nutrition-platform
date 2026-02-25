'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';

export default function TermsPage() {
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">服務協議</h1>
          <p className="text-sm text-gray-500 mb-8">最後更新日期：2024年1月20日</p>

          <div className="prose prose-gray max-w-none space-y-6">
            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">1. 服務說明</h2>
              <p className="text-gray-700 leading-relaxed">
                WysikHealth（以下簡稱「本平台」）提供基於人工智能的營養補充品推薦服務。本服務旨在根據用戶提供的生活型態問卷和健康數據，為用戶提供個性化的營養補充建議。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">2. 用戶責任</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                使用本平台服務時，您同意：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>提供真實、準確、完整的個人資訊</li>
                <li>妥善保管您的帳戶資訊和密碼</li>
                <li>不得將帳戶轉讓或出借給他人使用</li>
                <li>遵守所有適用的法律法規</li>
                <li>不得利用本平台從事任何違法或不當行為</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">3. 服務限制</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                您理解並同意：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>本平台提供的建議僅供參考，不構成醫療建議</li>
                <li>在開始任何補充劑計劃前，應諮詢專業醫療人員</li>
                <li>本平台不對用戶因使用建議而產生的任何後果負責</li>
                <li>本平台保留隨時修改、暫停或終止服務的權利</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">4. 知識產權</h2>
              <p className="text-gray-700 leading-relaxed">
                本平台的所有內容，包括但不限於文字、圖片、軟件、算法、商標等，均受知識產權法保護。未經本平台書面許可，您不得複製、修改、傳播或用於商業目的。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">5. 免責聲明</h2>
              <p className="text-gray-700 leading-relaxed mb-3">
                本平台在法律允許的最大範圍內：
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>不保證服務的準確性、完整性或可靠性</li>
                <li>不對因使用或無法使用服務而產生的任何損失負責</li>
                <li>不對第三方產品或服務的質量負責</li>
                <li>不對因不可抗力導致的服務中斷負責</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">6. 協議修改</h2>
              <p className="text-gray-700 leading-relaxed">
                本平台保留隨時修改本協議的權利。修改後的協議將在本頁面公布，並自公布之日起生效。您繼續使用本服務即表示接受修改後的協議。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">7. 法律適用與爭議解決</h2>
              <p className="text-gray-700 leading-relaxed">
                本協議的解釋、效力及爭議解決均適用中華民國法律。因本協議產生的任何爭議，雙方應首先通過友好協商解決；協商不成的，任何一方均可向本平台所在地有管轄權的法院提起訴訟。
              </p>
            </section>

            <section>
              <h2 className="text-xl font-bold text-gray-900 mb-3">8. 聯繫我們</h2>
              <p className="text-gray-700 leading-relaxed">
                如您對本協議有任何疑問或建議，請通過以下方式聯繫我們：
              </p>
              <p className="text-gray-700 mt-2">
                電子郵件：support@wysikhealth.com<br />
                客服時間：週一至週五 9:00-18:00
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
