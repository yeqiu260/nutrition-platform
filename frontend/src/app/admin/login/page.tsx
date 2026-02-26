'use client';
import { API_BASE_URL } from '@/lib/api/config';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

export default function AdminLoginPage() {
  const t = useTranslations('admin');
  const tCommon = useTranslations('common');
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    console.log('handleLogin called', { username, password: '***' });
    
    if (!username || !password) {
      setError(t('forms.submit'));
      return;
    }
    
    setError('');
    setLoading(true);

    try {
      console.log('Sending login request...');
      const res = await fetch(`${API_BASE_URL}/api/admin/login`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept-Language': typeof window !== 'undefined' ? localStorage.getItem('NEXT_LOCALE') || 'zh-TW' : 'zh-TW'
        },
        body: JSON.stringify({ username, password }),
      });

      console.log('Response status:', res.status);
      const data = await res.json();
      console.log('Response data:', data);
      
      if (!res.ok) {
        throw new Error(data.detail || tCommon('error'));
      }

      // 保存到 localStorage
      console.log('Saving to localStorage...');
      window.localStorage.setItem('admin_token', data.token);
      window.localStorage.setItem('admin_role', data.role);
      window.localStorage.setItem('admin_username', data.username);
      
      console.log('Saved! Token:', window.localStorage.getItem('admin_token')?.substring(0, 20) + '...');
      
      // 跳转到 dashboard
      console.log('Redirecting to dashboard...');
      window.location.href = '/admin/dashboard';
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.message || tCommon('error'));
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>{t('nav.dashboard')}</h1>
        
        <div style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>{t('products.name')}</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyPress={handleKeyPress}
              style={styles.input}
              placeholder={t('products.name')}
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>{tCommon('login')}</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyPress={handleKeyPress}
              style={styles.input}
              placeholder={tCommon('login')}
            />
          </div>

          {error && <div style={styles.error}>{error}</div>}

          <button 
            type="button" 
            onClick={handleLogin}
            style={styles.button} 
            disabled={loading}
          >
            {loading ? tCommon('loading') : tCommon('login')}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
  },
  card: {
    backgroundColor: '#fff',
    padding: '40px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '400px',
  },
  title: {
    textAlign: 'center',
    marginBottom: '30px',
    color: '#333',
    fontSize: '24px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    fontSize: '14px',
    color: '#666',
  },
  input: {
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '16px',
  },
  button: {
    padding: '14px',
    backgroundColor: '#d4a855',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    marginTop: '10px',
  },
  error: {
    color: '#e74c3c',
    fontSize: '14px',
    textAlign: 'center',
  },
};
