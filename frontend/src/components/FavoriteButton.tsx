'use client';
import { API_BASE_URL } from '@/lib/api/config';

import React, { useState, useEffect } from 'react';
import { Heart } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface FavoriteButtonProps {
  productId: string;
  onToggle?: (isFavorite: boolean) => void;
}

export function FavoriteButton({ productId, onToggle }: FavoriteButtonProps) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const t = useTranslations('errors');

  // 检查登录状态和收藏状态
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    setIsLoggedIn(!!token);
    
    // 只有登录时才检查收藏状态
    if (!token) return;

    const checkFavorite = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/user/favorites/check/${productId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setIsFavorite(data.is_favorite);
        } else if (response.status === 401) {
          // Token 过期，清除登录状态
          localStorage.removeItem('auth_token');
          setIsLoggedIn(false);
        }
      } catch (error) {
        // 静默失败，不影响用户体验
        console.debug('Failed to check favorite status:', error);
      }
    };

    checkFavorite();
  }, [productId]);

  const handleToggle = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      alert(t('loginRequired'));
      return;
    }

    setIsLoading(true);

    try {
      if (isFavorite) {
        // 移除收藏
        const response = await fetch(`${API_BASE_URL}/api/user/favorites/${productId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok || response.status === 204) {
          setIsFavorite(false);
          onToggle?.(false);
        } else if (response.status === 401) {
          localStorage.removeItem('auth_token');
          setIsLoggedIn(false);
          alert(t('sessionExpired'));
        } else {
          alert(t('removeFavoriteFailed'));
        }
      } else {
        // 添加收藏
        const response = await fetch(`${API_BASE_URL}/api/user/favorites`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ product_id: productId })
        });

        if (response.ok) {
          setIsFavorite(true);
          onToggle?.(true);
        } else if (response.status === 409) {
          // 已经收藏过了
          setIsFavorite(true);
        } else if (response.status === 401) {
          localStorage.removeItem('auth_token');
          setIsLoggedIn(false);
          alert(t('sessionExpired'));
        } else {
          alert(t('addFavoriteFailed'));
        }
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      alert(t('operationFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  // 未登录时显示灰色心形，提示需要登录
  return (
    <button
      onClick={handleToggle}
      disabled={isLoading}
      className="favorite-btn"
      title={isLoggedIn ? (isFavorite ? t('removeFavorite') : t('addFavorite')) : t('loginRequired')}
      style={{
        position: 'absolute',
        top: '8px',
        left: '8px',
        background: 'rgba(255, 255, 255, 0.9)',
        border: 'none',
        borderRadius: '50%',
        width: '36px',
        height: '36px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: isLoading ? 'not-allowed' : 'pointer',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        transition: 'all 0.2s',
        zIndex: 10,
        opacity: isLoggedIn ? 1 : 0.6
      }}
      onMouseEnter={(e) => {
        if (!isLoading) {
          e.currentTarget.style.transform = 'scale(1.1)';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
      }}
    >
      <Heart
        size={20}
        fill={isFavorite ? '#ef4444' : 'none'}
        stroke={isFavorite ? '#ef4444' : '#6b7280'}
        strokeWidth={2}
      />
    </button>
  );
}
