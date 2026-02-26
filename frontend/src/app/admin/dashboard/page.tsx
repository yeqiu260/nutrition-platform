'use client';
import { API_BASE_URL } from '@/lib/api/config';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';

interface SystemConfig {
  key: string;
  value: string;
  description: string;
  updated_at: string;
}

interface AdminUser {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function AdminDashboard() {
  const t = useTranslations('admin');
  const tCommon = useTranslations('common');

  const [activeTab, setActiveTab] = useState('config');
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Config form
  const [configKey, setConfigKey] = useState('');
  const [configValue, setConfigValue] = useState('');
  const [configDesc, setConfigDesc] = useState('');

  // User form
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('admin');

  const role = typeof window !== 'undefined' ? localStorage.getItem('admin_role') : '';

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('admin_token')}`,
    'Accept-Language': typeof window !== 'undefined' ? localStorage.getItem('NEXT_LOCALE') || 'zh-TW' : 'zh-TW'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [configRes, userRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/admin/config`, { headers: getHeaders() }),
        fetch(`${API_BASE_URL}/api/admin/users`, { headers: getHeaders() }),
      ]);
      if (configRes.ok) setConfigs(await configRes.json());
      if (userRes.ok) setUsers(await userRes.json());
    } catch (err) {
      console.error('Load error:', err);
    }
    setLoading(false);
  };

  const showMessage = (msg: string, isError = false) => {
    if (isError) setError(msg);
    else setMessage(msg);
    setTimeout(() => { setMessage(''); setError(''); }, 3000);
  };

  const handleSaveConfig = async () => {
    if (!configKey || !configValue) {
      showMessage(t('forms.submit'), true);
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/config`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({ key: configKey, value: configValue, description: configDesc }),
      });
      if (res.ok) {
        showMessage(tCommon('success'));
        setConfigKey(''); setConfigValue(''); setConfigDesc('');
        loadData();
      } else {
        const data = await res.json();
        showMessage(parseErrorMessage(data.detail), true);
      }
    } catch (err: any) {
      showMessage(err.message, true);
    }
  };

  const parseErrorMessage = (detail: any): string => {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map(d => d.msg || d.message || JSON.stringify(d)).join(', ');
    }
    if (typeof detail === 'object' && detail !== null) {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
    return tCommon('error');
  };

  const handleCreateUser = async () => {
    if (!newUsername || !newPassword) {
      showMessage(t('forms.submit'), true);
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/users`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ username: newUsername, password: newPassword, role: newRole }),
      });
      if (res.ok) {
        showMessage(tCommon('success'));
        setNewUsername(''); setNewPassword('');
        loadData();
      } else {
        const data = await res.json();
        showMessage(parseErrorMessage(data.detail), true);
      }
    } catch (err: any) {
      showMessage(err.message, true);
    }
  };

  const handleUpdateRole = async (userId: string, role: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/role`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({ user_id: userId, new_role: role }),
      });
      if (res.ok) {
        showMessage(tCommon('success'));
        loadData();
      }
    } catch (err: any) {
      showMessage(err.message, true);
    }
  };

  const handleDeleteUser = async (userId: string, username: string) => {
    if (!confirm(`${t('forms.delete')} ${username}?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      });
      if (res.ok) {
        showMessage(tCommon('success'));
        loadData();
      }
    } catch (err: any) {
      showMessage(err.message, true);
    }
  };

  const handleDeleteConfig = async (key: string) => {
    if (!confirm(`確定要刪除配置 ${key}？`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/config/${key}`, {
        method: 'DELETE',
        headers: getHeaders(),
      });
      if (res.ok) {
        showMessage(tCommon('success'));
        loadData();
      } else {
        const data = await res.json();
        showMessage(parseErrorMessage(data.detail), true);
      }
    } catch (err: any) {
      showMessage(err.message, true);
    }
  };

  const roleLabels: Record<string, string> = {
    super_admin: 'Super Admin',
    admin: 'Admin',
    partner: 'Partner',
    user: 'User',
  };

  if (loading) {
    return <div style={styles.loading}>{tCommon('loading')}</div>;
  }

  return (
    <div style={styles.container}>
      {message && <div style={styles.success}>{message}</div>}
      {error && <div style={styles.error}>{error}</div>}

      {/* 快捷导航卡片 */}
      <div style={styles.quickLinks}>
        <a href="/admin/products" style={styles.quickLinkCard}>
          <div style={styles.quickLinkIcon}>🛍️</div>
          <div style={styles.quickLinkTitle}>商品管理</div>
          <div style={styles.quickLinkDesc}>管理所有商品</div>
        </a>
        <a href="/admin/products/pending" style={styles.quickLinkCard}>
          <div style={styles.quickLinkIcon}>⏳</div>
          <div style={styles.quickLinkTitle}>待審核商品</div>
          <div style={styles.quickLinkDesc}>審核新商品</div>
        </a>
        <a href="/admin/analytics" style={styles.quickLinkCard}>
          <div style={styles.quickLinkIcon}>📊</div>
          <div style={styles.quickLinkTitle}>用戶行為分析</div>
          <div style={styles.quickLinkDesc}>查看事件追踪</div>
        </a>
        <a href="/admin/review" style={styles.quickLinkCard}>
          <div style={styles.quickLinkIcon}>✅</div>
          <div style={styles.quickLinkTitle}>審核隊列</div>
          <div style={styles.quickLinkDesc}>審核推薦結果</div>
        </a>
      </div>

      <div style={styles.tabs}>
        <button style={activeTab === 'config' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('config')}>
          {t('config.title')}
        </button>
        <button style={activeTab === 'users' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('users')}>
          {t('users.title')}
        </button>
      </div>

      {activeTab === 'config' && (
        <div>
          {role === 'super_admin' && (
            <div style={styles.card}>
              <h3 style={styles.cardTitle}>{t('config.add')}</h3>
              <div style={styles.formRow}>
                <input style={styles.input} placeholder={t('config.key')} value={configKey} onChange={e => setConfigKey(e.target.value)} />
                <input style={styles.input} placeholder={t('config.value')} value={configValue} onChange={e => setConfigValue(e.target.value)} />
              </div>
              <input style={{ ...styles.input, marginBottom: 10 }} placeholder={t('config.desc')} value={configDesc} onChange={e => setConfigDesc(e.target.value)} />
              <button style={styles.btn} onClick={handleSaveConfig}>{tCommon('submit')}</button>
            </div>
          )}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>{t('config.title')}</h3>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>{t('config.key')}</th>
                  <th style={styles.th}>{t('config.value')}</th>
                  <th style={styles.th}>{t('config.desc')}</th>
                  <th style={styles.th}>{t('config.updated_at')}</th>
                  {role === 'super_admin' && <th style={styles.th}>{tCommon('submit')}</th>}
                </tr>
              </thead>
              <tbody>
                {configs.map(c => (
                  <tr key={c.key}>
                    <td style={styles.td}>{c.key}</td>
                    <td style={styles.td}>{c.value}</td>
                    <td style={styles.td}>{c.description || '-'}</td>
                    <td style={styles.td}>{new Date(c.updated_at).toLocaleString()}</td>
                    {role === 'super_admin' && (
                      <td style={styles.td}>
                        <button style={styles.deleteBtn} onClick={() => handleDeleteConfig(c.key)}>
                          {t('forms.delete')}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {configs.length === 0 && <tr><td colSpan={role === 'super_admin' ? 5 : 4} style={styles.empty}>{tCommon('loading')}</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div>
          {role === 'super_admin' && (
            <div style={styles.card}>
              <h3 style={styles.cardTitle}>{t('users.add')}</h3>
              <div style={styles.formRow}>
                <input style={styles.input} placeholder={t('users.name')} value={newUsername} onChange={e => setNewUsername(e.target.value)} />
                <input style={styles.input} type="password" placeholder={tCommon('login')} value={newPassword} onChange={e => setNewPassword(e.target.value)} />
                <select style={styles.select} value={newRole} onChange={e => setNewRole(e.target.value)}>
                  <option value="admin">Admin</option>
                  <option value="partner">Partner</option>
                  <option value="user">User</option>
                </select>
                <button style={styles.btn} onClick={handleCreateUser}>{tCommon('submit')}</button>
              </div>
            </div>
          )}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>{t('users.title')}</h3>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>{t('users.name')}</th>
                  <th style={styles.th}>{t('users.role')}</th>
                  <th style={styles.th}>{t('users.status')}</th>
                  <th style={styles.th}>{t('users.created_at')}</th>
                  {role === 'super_admin' && <th style={styles.th}>{tCommon('submit')}</th>}
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td style={styles.td}>{u.username}</td>
                    <td style={styles.td}>
                      {role === 'super_admin' && u.role !== 'super_admin' ? (
                        <select style={styles.selectSmall} value={u.role} onChange={e => handleUpdateRole(u.id, e.target.value)}>
                          <option value="admin">Admin</option>
                          <option value="partner">Partner</option>
                          <option value="user">User</option>
                        </select>
                      ) : roleLabels[u.role] || u.role}
                    </td>
                    <td style={styles.td}>
                      <span style={u.is_active ? styles.active : styles.inactive}>{u.is_active ? 'Active' : 'Inactive'}</span>
                    </td>
                    <td style={styles.td}>{new Date(u.created_at).toLocaleString()}</td>
                    {role === 'super_admin' && (
                      <td style={styles.td}>
                        {u.role !== 'super_admin' && (
                          <button style={styles.deleteBtn} onClick={() => handleDeleteUser(u.id, u.username)}>{t('forms.delete')}</button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: 30 },
  loading: { padding: 50, textAlign: 'center' },
  success: { backgroundColor: '#d4edda', color: '#155724', padding: 12, marginBottom: 20, borderRadius: 4 },
  error: { backgroundColor: '#f8d7da', color: '#721c24', padding: 12, marginBottom: 20, borderRadius: 4 },
  quickLinks: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 16,
    marginBottom: 32
  },
  quickLinkCard: {
    backgroundColor: '#fff',
    padding: 24,
    borderRadius: 12,
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    textDecoration: 'none',
    color: '#333',
    transition: 'all 0.2s',
    cursor: 'pointer',
    border: '1px solid #f0f0f0',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  quickLinkIcon: {
    fontSize: 40,
    marginBottom: 12
  },
  quickLinkTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#111'
  },
  quickLinkDesc: {
    fontSize: 13,
    color: '#666'
  },
  tabs: { display: 'flex', gap: 0, marginBottom: 20, borderBottom: '1px solid #ddd' },
  tab: { padding: '12px 25px', border: 'none', borderBottom: '3px solid transparent', background: 'none', cursor: 'pointer', fontSize: 15, color: '#666' },
  tabActive: { padding: '12px 25px', border: 'none', borderBottom: '3px solid #d4a855', background: 'none', cursor: 'pointer', fontSize: 15, color: '#333', fontWeight: 'bold' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 8, marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
  cardTitle: { margin: '0 0 15px', fontSize: 16 },
  formRow: { display: 'flex', gap: 10, marginBottom: 10, flexWrap: 'wrap' },
  input: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: 4, fontSize: 14, flex: 1, minWidth: 150 },
  select: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: 4, fontSize: 14, minWidth: 120 },
  selectSmall: { padding: '6px 10px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13 },
  btn: { padding: '10px 20px', backgroundColor: '#d4a855', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 },
  deleteBtn: { padding: '6px 12px', backgroundColor: '#e74c3c', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { backgroundColor: '#f8f9fa', padding: '12px 15px', textAlign: 'left', fontSize: 14, color: '#666', borderBottom: '1px solid #ddd' },
  td: { padding: '12px 15px', borderBottom: '1px solid #eee', fontSize: 14 },
  empty: { padding: 30, textAlign: 'center', color: '#999' },
  active: { backgroundColor: '#d4edda', color: '#155724', padding: '4px 10px', borderRadius: 12, fontSize: 12 },
  inactive: { backgroundColor: '#f8d7da', color: '#721c24', padding: '4px 10px', borderRadius: 12, fontSize: 12 },
};
