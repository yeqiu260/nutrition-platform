'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, AlertCircle, ShoppingCart } from 'lucide-react';
import { HealthDataDisplay } from '@/components/HealthDataDisplay';
import { FavoriteButton } from '@/components/FavoriteButton';

interface HistoryDetail {
  id: string;
  session_id: string;
  created_at: string;
  answers: any[];
  health_data: any;
  recommendations: {
    items: Array<{
      rank: number;
      supplement_id: string;
      name: string;
      group: string;
      why: string[];
      safety: string[];
      confidence: number;
      recommended_products: Array<{
        product_id: string;
        product_name: string;
        why_this_product: string[];
        price?: number;
        currency: string;
        purchase_url: string;
        image_url?: string;
        partner_name?: string;
      }>;
    }>;
    disclaimer: string;
  };
  ai_generated: boolean;
}

export default function HistoryDetailPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;
  
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDetail();
  }, [sessionId]);

  const fetchDetail = async () => {
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
      setError('請先登入查看歷史記錄');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/user/history/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.status === 401) {
        setError('登入已過期，請重新登入');
        localStorage.removeItem('auth_token');
        setLoading(false);
        return;
      }

      if (response.status === 404) {
        setError('找不到此歷史記錄');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error('獲取歷史記錄失敗');
      }

      const data = await response.json();
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '獲取歷史記錄失敗');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-gray-200 border-t-yellow-400 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">載入中...</p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">無法載入歷史記錄</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push('/history')}
            className="px-6 py-3 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors"
          >
            返回列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <button
            onClick={() => router.push('/history')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回列表
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">推薦結果詳情</h1>
              <p className="text-sm text-gray-600 mt-1">
                {formatDate(detail.created_at)}
                {detail.ai_generated && (
                  <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded">
                    AI 生成
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* 化验值展示 */}
        {detail.health_data && (
          <div className="mb-6">
            <HealthDataDisplay data={detail.health_data} />
          </div>
        )}

        {/* 推荐结果 */}
        <div className="space-y-6">
          {detail.recommendations.items.map((rec) => (
            <div key={rec.supplement_id} className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-start gap-4 mb-4">
                <div className="w-10 h-10 bg-yellow-400 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-lg font-bold text-gray-900">{rec.rank}</span>
                </div>
                <div className="flex-1">
                  <div className="text-sm text-gray-600 mb-1">{rec.group}</div>
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{rec.name}</h3>
                  
                  {/* AI 推荐原因 */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <p className="text-sm font-semibold text-gray-900 mb-2">✨ AI 分析原因：</p>
                    <ul className="space-y-1">
                      {rec.why.map((reason, i) => (
                        <li key={i} className="text-sm text-gray-700">• {reason}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 安全提示 */}
                  {rec.safety && rec.safety.length > 0 && (
                    <div className="bg-amber-50 border-l-4 border-amber-400 rounded-lg p-4 mb-4">
                      <p className="text-sm font-semibold text-amber-900 mb-2">⚠️ 安全提示：</p>
                      <ul className="space-y-1">
                        {rec.safety.map((warning, i) => (
                          <li key={i} className="text-sm text-amber-800">• {warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="text-sm text-gray-600">
                    信心度：<span className="font-semibold">{rec.confidence}%</span>
                  </div>
                </div>
              </div>

              {/* 推荐商品 */}
              {rec.recommended_products && rec.recommended_products.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <ShoppingCart className="w-5 h-5" />
                    推薦商品
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {rec.recommended_products.map((product) => (
                      <div key={product.product_id} className="relative bg-gray-50 rounded-lg p-4 hover:shadow-md transition-shadow">
                        {/* 收藏按钮 */}
                        <div style={{ position: 'absolute', top: '8px', left: '8px', zIndex: 10 }}>
                          <FavoriteButton productId={product.product_id} />
                        </div>

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
                          className="w-full h-40 object-cover rounded-lg mb-3"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = 'https://placehold.co/360x360/e0e0e0/555?text=Product';
                          }}
                        />
                        <h5 className="font-semibold text-gray-900 mb-1 line-clamp-2">
                          {product.product_name}
                        </h5>
                        {product.partner_name && (
                          <p className="text-xs text-gray-600 mb-2">by {product.partner_name}</p>
                        )}
                        <p className="text-lg font-bold text-gray-900 mb-3">
                          {product.price ? `${product.currency} ${product.price}` : '價格洽詢'}
                        </p>
                        
                        {/* AI 推荐理由 */}
                        {product.why_this_product && product.why_this_product.length > 0 && (
                          <div className="bg-yellow-50 rounded-lg p-3 mb-3">
                            <p className="text-xs font-semibold text-yellow-900 mb-1">✨ 推薦理由：</p>
                            <ul className="space-y-1">
                              {product.why_this_product.map((reason, i) => (
                                <li key={i} className="text-xs text-yellow-800">→ {reason}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <a
                          href={product.purchase_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block w-full text-center px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors"
                        >
                          前往購買
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 免责声明 */}
        <div className="mt-8 bg-gray-100 rounded-lg p-6">
          <p className="text-sm text-gray-600 leading-relaxed">
            {detail.recommendations.disclaimer}
          </p>
        </div>
      </div>
    </div>
  );
}
