/**
 * SEO 工具类
 * 处理元数据、结构化数据和 SEO 优化
 */

export interface PageMetadata {
  title: string;
  description: string;
  keywords?: string[];
  image?: string;
  url?: string;
  type?: 'website' | 'article' | 'product';
  locale?: string;
}

export interface StructuredData {
  '@context': string;
  '@type': string;
  [key: string]: any;
}

/**
 * 语言特定的元数据
 */
export const localeMetadata: Record<string, PageMetadata> = {
  'en': {
    title: 'WysikHealth - Personalized Nutrition Recommendations',
    description: 'Get personalized supplement recommendations based on your lifestyle and health status through our AI-powered questionnaire.',
    keywords: ['nutrition', 'supplements', 'health', 'personalized', 'AI', 'recommendations'],
    type: 'website',
    locale: 'en_US',
  },
  'zh-TW': {
    title: 'WysikHealth - 個性化營養補充建議',
    description: '透過 AI 分析您的生活型態和健康狀況，獲得量身定制的營養補充建議。',
    keywords: ['營養補充', '補充品', '健康', '個性化推薦', 'AI', '分析'],
    type: 'website',
    locale: 'zh_TW',
  },
};

/**
 * 页面特定的元数据
 */
export const pageMetadata: Record<string, Record<string, PageMetadata>> = {
  'en': {
    'landing': {
      title: 'WysikHealth - Personalized Nutrition Recommendations',
      description: 'Stop guessing. Find the supplements your body truly needs through our AI-powered analysis.',
      keywords: ['nutrition', 'supplements', 'health', 'personalized', 'AI'],
      type: 'website',
    },
    'quiz': {
      title: 'Health Questionnaire - WysikHealth',
      description: 'Complete our 5-minute health questionnaire to get personalized supplement recommendations.',
      keywords: ['health questionnaire', 'nutrition assessment', 'supplement recommendations'],
      type: 'website',
    },
    'results': {
      title: 'Your Personalized Recommendations - WysikHealth',
      description: 'View your personalized supplement recommendations based on your health profile.',
      keywords: ['supplement recommendations', 'personalized health', 'nutrition advice'],
      type: 'website',
    },
  },
  'zh-TW': {
    'landing': {
      title: 'WysikHealth - 個性化營養補充建議',
      description: '不再盲目補充，透過 AI 分析找出身體真正需要的營養補充品。',
      keywords: ['營養補充', '補充品', '健康', '個性化推薦', 'AI'],
      type: 'website',
    },
    'quiz': {
      title: '健康問卷 - WysikHealth',
      description: '完成 5 分鐘的健康問卷，獲得個性化的營養補充建議。',
      keywords: ['健康問卷', '營養評估', '補充品推薦'],
      type: 'website',
    },
    'results': {
      title: '您的個性化推薦 - WysikHealth',
      description: '根據您的健康檔案查看個性化的營養補充建議。',
      keywords: ['補充品推薦', '個性化健康', '營養建議'],
      type: 'website',
    },
  },
};

/**
 * 获取页面元数据
 */
export function getPageMetadata(locale: string, page: string): PageMetadata {
  const metadata = pageMetadata[locale]?.[page] || pageMetadata['zh-TW']?.[page];
  return metadata || localeMetadata[locale] || localeMetadata['zh-TW'];
}

/**
 * 生成 hreflang 标签
 */
export function generateHrefLangTags(baseUrl: string, path: string = ''): string {
  const locales = ['en', 'zh-TW'];
  const tags = locales
    .map(locale => `<link rel="alternate" hrefLang="${locale}" href="${baseUrl}/${locale}${path}" />`)
    .join('\n');
  
  // 添加 x-default
  return tags + `\n<link rel="alternate" hrefLang="x-default" href="${baseUrl}/zh-TW${path}" />`;
}

/**
 * 生成 Open Graph 标签
 */
export function generateOpenGraphTags(metadata: PageMetadata, url: string): Record<string, string> {
  return {
    'og:title': metadata.title,
    'og:description': metadata.description,
    'og:url': url,
    'og:type': metadata.type || 'website',
    'og:site_name': 'WysikHealth',
    ...(metadata.image && { 'og:image': metadata.image }),
    ...(metadata.locale && { 'og:locale': metadata.locale }),
  };
}

/**
 * 生成 Twitter 卡片标签
 */
export function generateTwitterCardTags(metadata: PageMetadata): Record<string, string> {
  return {
    'twitter:card': 'summary_large_image',
    'twitter:title': metadata.title,
    'twitter:description': metadata.description,
    ...(metadata.image && { 'twitter:image': metadata.image }),
  };
}

/**
 * 生成组织结构化数据
 */
export function generateOrganizationSchema(baseUrl: string): StructuredData {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'WysikHealth',
    url: baseUrl,
    logo: `${baseUrl}/logo.png`,
    description: 'AI-powered personalized nutrition recommendation platform',
    sameAs: [
      'https://www.facebook.com/wysikhealth',
      'https://www.instagram.com/wysikhealth',
      'https://twitter.com/wysikhealth',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'Customer Support',
      email: 'support@wysikhealth.com',
    },
  };
}

/**
 * 生成产品结构化数据
 */
export function generateProductSchema(
  name: string,
  description: string,
  price: number,
  currency: string,
  image?: string
): StructuredData {
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name,
    description,
    image,
    offers: {
      '@type': 'Offer',
      price: price.toString(),
      priceCurrency: currency,
    },
  };
}

/**
 * 生成文章结构化数据
 */
export function generateArticleSchema(
  headline: string,
  description: string,
  image?: string,
  datePublished?: string,
  dateModified?: string
): StructuredData {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline,
    description,
    image,
    datePublished: datePublished || new Date().toISOString(),
    dateModified: dateModified || new Date().toISOString(),
    author: {
      '@type': 'Organization',
      name: 'WysikHealth',
    },
  };
}

/**
 * 生成常见问题结构化数据
 */
export function generateFAQSchema(
  faqs: Array<{ question: string; answer: string }>
): StructuredData {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(faq => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };
}

/**
 * 生成面包屑结构化数据
 */
export function generateBreadcrumbSchema(
  items: Array<{ name: string; url: string }>
): StructuredData {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

/**
 * 获取当前语言
 */
export function getCurrentLocale(): string {
  if (typeof window === 'undefined') {
    return 'zh-TW';
  }
  return localStorage.getItem('NEXT_LOCALE') || 'zh-TW';
}

/**
 * 生成规范 URL
 */
export function generateCanonicalUrl(baseUrl: string, path: string, locale: string): string {
  return `${baseUrl}/${locale}${path}`;
}

/**
 * 生成替代语言 URL
 */
export function generateAlternateUrls(baseUrl: string, path: string): Record<string, string> {
  const locales = ['en', 'zh-TW'];
  const urls: Record<string, string> = {};
  
  locales.forEach(locale => {
    urls[locale] = `${baseUrl}/${locale}${path}`;
  });
  
  urls['x-default'] = `${baseUrl}/zh-TW${path}`;
  
  return urls;
}

/**
 * 验证元数据
 */
export function validateMetadata(metadata: PageMetadata): boolean {
  return !!(
    metadata.title &&
    metadata.title.length > 0 &&
    metadata.title.length <= 60 &&
    metadata.description &&
    metadata.description.length > 0 &&
    metadata.description.length <= 160
  );
}

/**
 * 获取元数据验证错误
 */
export function getMetadataValidationErrors(metadata: PageMetadata): string[] {
  const errors: string[] = [];
  
  if (!metadata.title || metadata.title.length === 0) {
    errors.push('Title is required');
  } else if (metadata.title.length > 60) {
    errors.push(`Title is too long (${metadata.title.length}/60)`);
  }
  
  if (!metadata.description || metadata.description.length === 0) {
    errors.push('Description is required');
  } else if (metadata.description.length > 160) {
    errors.push(`Description is too long (${metadata.description.length}/160)`);
  }
  
  return errors;
}
