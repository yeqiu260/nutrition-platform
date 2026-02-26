'use client';
import { API_BASE_URL } from '@/lib/api/config';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Heart, Trash2, AlertCircle, ShoppingCart } from 'lucide-react';

interface FavoriteItem {
  id: string;
  product_id: string;
  product_name: string;
  product_image: string | null;
  partner_name: string | null;
  price: number | null;
  currency: string;
  note: string | null;
  created_at: string;
}

export default function FavoritesPage() {
  const router = useRouter();
  const t = useTranslations('favorites');
  const tCommon = useTranslations('common');
  const tErrors = useTranslations('errors');
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  useEffect(() => {
    fetchFavorites();
  }, []);

  const fetchFavorites = async () => {
    const token = localStorage.getItem('auth_token');

    if (!token) {
      setError(tErrors('loginRequired'));
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/user/favorites`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.status === 401) {
        setError(tErrors('sessionExpired'));
        localStorage.removeItem('auth_token');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(tErrors('fetchFailed'));
      }

      const data = await response.json();
      setFavorites(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : tErrors('fetchFailed'));
    } finally {
      setLoading(false);
    }
  };

  const removeFavorite = async (productId: string) => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    setRemovingId(productId);

    try {
      const response = await fetch(`${API_BASE_URL}/api/user/favorites/${productId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok || response.status === 404) {
        // 从列表中移除
        setFavorites(favorites.filter(f => f.product_id !== productId));
      } else {
        alert(tErrors('removeFavoriteFailed'));
      }
    } catch (err) {
      alert(tErrors('removeFavoriteFailed'));
    } finally {
      setRemovingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-gray-200 border-t-yellow-400 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{tCommon('loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md bg-white rounded-xl shadow-lg p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">{t('loadError')}</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors"
          >
            {tCommon('backToHome')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Heart className="w-6 h-6 text-red-500" fill="currentColor" />
              <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
              <span className="px-3 py-1 bg-gray-100 text-gray-700 text-sm font-medium rounded-full">
                {t('itemCount', { count: favorites.length })}
              </span>
            </div>
            <button
              onClick={() => router.push('/')}
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              {tCommon('backToHome')}
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        {favorites.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <Heart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">{t('empty.title')}</h3>
            <p className="text-gray-600 mb-6">{t('empty.description')}</p>
            <button
              onClick={() => router.push('/')}
              className="px-6 py-3 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors"
            >
              {t('empty.startQuiz')}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {favorites.map((item) => (
              <div
                key={item.id}
                className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden"
              >
                {/* 商品图片 */}
                <div className="relative">
                  <img
                    src={item.product_image?.startsWith('/api/')
                      ? `http://localhost:8000${item.product_image}`
                      : item.product_image || 'https://placehold.co/360x360/e0e0e0/555?text=Product'
                    }
                    alt={item.product_name}
                    className="w-full h-48 object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'https://placehold.co/360x360/e0e0e0/555?text=Product';
                    }}
                  />

                  {/* Sponsored 标签 */}
                  {item.partner_name && (
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

                  {/* 移除按钮 */}
                  <button
                    onClick={() => removeFavorite(item.product_id)}
                    disabled={removingId === item.product_id}
                    className="absolute top-2 left-2 p-2 bg-white rounded-full shadow-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                    title={t('remove')}
                  >
                    {removingId === item.product_id ? (
                      <div className="w-5 h-5 border-2 border-gray-300 border-t-red-500 rounded-full animate-spin"></div>
                    ) : (
                      <Trash2 className="w-5 h-5 text-red-500" />
                    )}
                  </button>
                </div>

                {/* 商品信息 */}
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 min-h-[3rem]">
                    {item.product_name}
                  </h3>

                  {item.partner_name && (
                    <p className="text-sm text-gray-600 mb-2">
                      by {item.partner_name}
                    </p>
                  )}

                  <div className="flex items-center justify-between mb-3">
                    <p className="text-lg font-bold text-gray-900">
                      {item.price ? `${item.currency} ${item.price}` : t('priceInquiry')}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatDate(item.created_at)}
                    </p>
                  </div>

                  {item.note && (
                    <p className="text-sm text-gray-600 mb-3 p-2 bg-gray-50 rounded">
                      {item.note}
                    </p>
                  )}

                  <button
                    onClick={() => {
                      // 这里可以添加查看商品详情或直接购买的逻辑
                      // 暂时先显示提示
                      alert(t('productDetailComingSoon'));
                    }}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors"
                  >
                    <ShoppingCart className="w-4 h-4" />
                    {t('viewProduct')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
