'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Mail, X } from 'lucide-react';

interface LoginViewProps {
  onLogin: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLogin }) => {
  const t = useTranslations('auth');
  const tCommon = useTranslations('common');
  
  const [step, setStep] = useState<'contact' | 'otp' | 'consent'>('contact');
  const [contactType, setContactType] = useState<'email' | 'phone'>('email');
  const [contact, setContact] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(0);
  
  // Consent state
  const [healthConsent, setHealthConsent] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);

  // Countdown effect
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/send-otp', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept-Language': typeof window !== 'undefined' ? localStorage.getItem('NEXT_LOCALE') || 'zh-TW' : 'zh-TW'
        },
        body: JSON.stringify({
          email: contactType === 'email' ? contact : undefined,
          phone: contactType === 'phone' ? contact : undefined,
          purpose: 'login'
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || t('errors.send_failed'));
      }

      setStep('otp');
      setCountdown(60);
      console.log('✓ OTP sent successfully');
    } catch (err: any) {
      setError(err.message || t('errors.send_failed'));
      console.error('Send OTP error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/verify-otp', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept-Language': typeof window !== 'undefined' ? localStorage.getItem('NEXT_LOCALE') || 'zh-TW' : 'zh-TW'
        },
        body: JSON.stringify({
          email: contactType === 'email' ? contact : undefined,
          phone: contactType === 'phone' ? contact : undefined,
          code: otp,
          purpose: 'login',
          consents: healthConsent ? {
            terms: true,
            privacy: true,
            health_data: healthConsent,
            marketing: marketingConsent
          } : undefined
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || t('errors.verify_failed'));
      }

      // If new user and hasn't agreed to terms, show consent page
      if (data.is_new_user && !healthConsent) {
        setStep('consent');
        return;
      }

      // Save user info
      if (data.user_id) {
        localStorage.setItem('user_id', data.user_id);
        localStorage.setItem('user_email', data.email || '');
      }

      console.log('✓ Login successful:', data);
      onLogin();
    } catch (err: any) {
      setError(err.message || t('errors.verify_failed'));
      console.error('Verify OTP error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConsentSubmit = async () => {
    if (!healthConsent) {
      setError(t('consent.mustAgree'));
      return;
    }
    // Re-submit verification with consent
    await handleVerifyOTP(new Event('submit') as any);
  };

  return (
    <div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-gray-100">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-yellow-400 rounded-xl flex items-center justify-center font-bold text-gray-900 text-2xl mx-auto mb-4">
            W
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            {step === 'contact' && t('welcome')}
            {step === 'otp' && t('otp.title')}
            {step === 'consent' && t('consent.title')}
          </h2>
          <p className="text-gray-500 mt-2">
            {step === 'contact' && t('contactMethod')}
            {step === 'otp' && t('otp.subtitle', { contact })}
            {step === 'consent' && t('consent.subtitle')}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        {/* Step 1: Enter contact info */}
        {step === 'contact' && (
          <form onSubmit={handleSendOTP} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('contactMethod')}</label>
              <div className="flex gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => setContactType('email')}
                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                    contactType === 'email'
                      ? 'bg-yellow-400 text-gray-900'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <Mail size={16} className="inline mr-1" />
                  {t('email')}
                </button>
                <button
                  type="button"
                  onClick={() => setContactType('phone')}
                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                    contactType === 'phone'
                      ? 'bg-yellow-400 text-gray-900'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  📱 {t('phone')}
                </button>
              </div>
              <div className="relative">
                <input
                  type={contactType === 'email' ? 'email' : 'tel'}
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all"
                  placeholder={contactType === 'email' ? t('emailPlaceholder') : t('phonePlaceholder')}
                  required
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !contact}
              className="w-full bg-gray-900 text-white font-bold py-3.5 rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all transform active:scale-[0.98] shadow-lg shadow-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('sending') : t('sendCode')}
            </button>
          </form>
        )}

        {/* Step 2: Enter OTP */}
        {step === 'otp' && (
          <form onSubmit={handleVerifyOTP} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('otp.label')}</label>
              <input
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all text-center text-2xl tracking-widest font-mono"
                placeholder={t('otp.placeholder')}
                maxLength={6}
                required
              />
              <p className="mt-2 text-xs text-gray-500 text-center">
                {t('otp.hint', { contact })}
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="w-full bg-gray-900 text-white font-bold py-3.5 rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all transform active:scale-[0.98] shadow-lg shadow-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('otp.verifying') : t('otp.submit')}
            </button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => {
                  if (countdown === 0) {
                    handleSendOTP(new Event('submit') as any);
                  }
                }}
                disabled={countdown > 0}
                className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {countdown > 0 ? t('otp.resendCountdown', { seconds: countdown }) : t('otp.resend')}
              </button>
              <span className="mx-2 text-gray-300">|</span>
              <button
                type="button"
                onClick={() => {
                  setStep('contact');
                  setOtp('');
                  setError('');
                }}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                {t('otp.changeContact')}
              </button>
            </div>
          </form>
        )}

        {/* Step 3: Consent */}
        {step === 'consent' && (
          <div className="space-y-6">
            <div className="bg-gray-50 rounded-xl p-4 max-h-64 overflow-y-auto text-sm text-gray-600 space-y-3">
              <h3 className="font-bold text-gray-900">{t('consent.healthDataTitle')}</h3>
              <p>{t('consent.healthDataText')}</p>
              <h3 className="font-bold text-gray-900 mt-4">{t('consent.disclaimerTitle')}</h3>
              <p>{t('consent.disclaimerText')}</p>
            </div>

            <div className="space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={healthConsent}
                  onChange={(e) => setHealthConsent(e.target.checked)}
                  className="mt-1 w-5 h-5 text-yellow-400 border-gray-300 rounded focus:ring-yellow-400"
                />
                <span className="text-sm text-gray-700">
                  {t('consent.healthConsentLabel')}
                </span>
              </label>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={marketingConsent}
                  onChange={(e) => setMarketingConsent(e.target.checked)}
                  className="mt-1 w-5 h-5 text-yellow-400 border-gray-300 rounded focus:ring-yellow-400"
                />
                <span className="text-sm text-gray-700">
                  {t('consent.marketingConsentLabel')}
                </span>
              </label>
            </div>

            <button
              onClick={handleConsentSubmit}
              disabled={!healthConsent || loading}
              className="w-full bg-gray-900 text-white font-bold py-3.5 rounded-full hover:bg-yellow-400 hover:text-gray-900 transition-all transform active:scale-[0.98] shadow-lg shadow-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('consent.processing') : t('consent.agreeAndContinue')}
            </button>
          </div>
        )}

        <div className="mt-8 text-center text-sm">
          <span className="text-gray-500">
            {step === 'contact' ? t('footer.loginAgree') : t('footer.needHelp')}
          </span>
          <a href="#" className="font-bold text-gray-900 ml-1 hover:underline decoration-yellow-400 decoration-2">
            {step === 'contact' ? t('footer.terms') : t('footer.contactSupport')}
          </a>
        </div>
      </div>
    </div>
  );
};
