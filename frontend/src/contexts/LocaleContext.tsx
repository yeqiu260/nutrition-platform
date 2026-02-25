'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { NextIntlClientProvider } from 'next-intl';

// 直接导入默认翻译
import defaultMessages from '../../messages/zh-TW.json';

type Locale = 'zh-TW' | 'en';

interface LocaleContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined);

export function useLocaleContext() {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error('useLocaleContext must be used within LocaleProvider');
  }
  return context;
}

interface LocaleProviderProps {
  children: ReactNode;
  initialLocale?: Locale;
}

export function LocaleProvider({ children, initialLocale = 'zh-TW' }: LocaleProviderProps) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const [messages, setMessages] = useState<any>(defaultMessages);
  const [isInitialized, setIsInitialized] = useState(false);

  // 初始化：从 localStorage 读取用户偏好（只执行一次）
  useEffect(() => {
    try {
      const savedLocale = localStorage.getItem('preferredLocale') as Locale;
      if (savedLocale && (savedLocale === 'zh-TW' || savedLocale === 'en')) {
        setLocaleState(savedLocale);
      }
    } catch (error) {
      console.warn('Failed to read language preference:', error);
    }
    setIsInitialized(true);
  }, []);

  // 加载翻译文件
  useEffect(() => {
    if (!isInitialized) return;

    const loadMessages = async () => {
      try {
        const msgs = await import(`../../messages/${locale}.json`);
        setMessages(msgs.default);
      } catch (error) {
        console.error('Failed to load messages:', error);
        // 如果加载失败，使用默认翻译
        setMessages(defaultMessages);
      }
    };
    loadMessages();
  }, [locale, isInitialized]);

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    // 保存到 localStorage
    try {
      localStorage.setItem('preferredLocale', newLocale);
    } catch (error) {
      console.warn('Failed to save language preference:', error);
    }
  };

  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      <NextIntlClientProvider locale={locale} messages={messages} timeZone="Asia/Taipei">
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}
