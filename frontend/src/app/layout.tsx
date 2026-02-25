import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { LocaleProvider } from '@/contexts/LocaleContext';
import './globals.css';

const inter = Inter({ subsets: ['latin', 'latin-ext'] });

export const metadata: Metadata = {
  title: {
    default: 'WysikHealth - Personalized Nutrition Recommendations',
    template: '%s | WysikHealth'
  },
  description: 'Get personalized supplement recommendations based on your lifestyle and health status through our AI-powered questionnaire.',
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || 'https://wysikhealth.com'),
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  icons: {
    icon: '/favicon.ico',
  },
  manifest: '/site.webmanifest',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#ffffff" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Organization',
              name: 'WysikHealth',
              url: process.env.NEXT_PUBLIC_BASE_URL || 'https://wysikhealth.com',
              logo: `${process.env.NEXT_PUBLIC_BASE_URL || 'https://wysikhealth.com'}/logo.png`,
              description: 'AI-powered personalized nutrition recommendation platform',
              sameAs: [
                'https://www.facebook.com/wysikhealth',
                'https://www.instagram.com/wysikhealth',
                'https://twitter.com/wysikhealth'
              ]
            })
          }}
        />
      </head>
      <body className={inter.className}>
        <LocaleProvider initialLocale="zh-TW">
          <main className="min-h-screen bg-gray-50">
            {children}
          </main>
        </LocaleProvider>
      </body>
    </html>
  );
}
