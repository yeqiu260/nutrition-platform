'use client';

import { Globe } from 'lucide-react';
import { useState } from 'react';

interface MainPageLanguageSwitcherProps {
  currentLocale: string;
  onLocaleChange: (locale: string) => void;
  className?: string;
}

export function MainPageLanguageSwitcher({ 
  currentLocale, 
  onLocaleChange,
  className 
}: MainPageLanguageSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);

  const switchLanguage = (newLocale: string) => {
    onLocaleChange(newLocale);
    setIsOpen(false);
    
    // 保存用户偏好
    try {
      localStorage.setItem('preferredLocale', newLocale);
    } catch (error) {
      console.warn('Failed to save language preference:', error);
    }
  };

  const displayText = currentLocale === 'zh-TW' ? '繁中' : 'EN';

  return (
    <div className={`relative ${className || ''}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        aria-label="Switch language"
      >
        <Globe size={18} />
        <span className="text-sm font-medium">{displayText}</span>
      </button>

      {isOpen && (
        <>
          {/* 点击外部关闭下拉菜单 */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute right-0 mt-2 w-32 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
            <button
              onClick={() => switchLanguage('zh-TW')}
              className={`w-full text-left px-4 py-2 text-sm rounded-t-lg transition-colors ${
                currentLocale === 'zh-TW'
                  ? 'bg-blue-50 text-blue-600 font-medium'
                  : 'hover:bg-gray-50'
              }`}
            >
              繁體中文
            </button>
            <button
              onClick={() => switchLanguage('en')}
              className={`w-full text-left px-4 py-2 text-sm rounded-b-lg transition-colors ${
                currentLocale === 'en'
                  ? 'bg-blue-50 text-blue-600 font-medium'
                  : 'hover:bg-gray-50'
              }`}
            >
              English
            </button>
          </div>
        </>
      )}
    </div>
  );
}
