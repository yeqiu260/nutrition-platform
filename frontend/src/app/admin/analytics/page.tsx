'use client';
import { API_BASE_URL } from '@/lib/api/config';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface EventSummary {
  event_type: string;
  count: number;
  first_at: string;
  last_at: string;
}

interface AnalyticsEvent {
  id: string;
  user_id: string;
  session_id: string | null;
  event_type: string;
  event_data: any;
  created_at: string;
  ip_address: string | null;
  user_agent: string | null;
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<EventSummary[]>([]);
  const [recentEvents, setRecentEvents] = useState<AnalyticsEvent[]>([]);
  const [selectedEventType, setSelectedEventType] = useState<string>('all');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalytics();
  }, [selectedEventType]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('admin_token');
      if (!token) {
        router.push('/admin/login');
        return;
      }

      // 获取事件统计摘要
      const summaryResponse = await fetch(`${API_BASE_URL}/api/analytics/admin/summary`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!summaryResponse.ok) {
        throw new Error('Failed to fetch analytics summary');
      }

      const summaryData = await summaryResponse.json();
      setSummary(summaryData);

      // 获取最近事件
      const eventsUrl = selectedEventType === 'all'
        ? `${API_BASE_URL}/api/analytics/admin/events?page=1&page_size=20`
        : `${API_BASE_URL}/api/analytics/admin/events?event_type=${selectedEventType}&page=1&page_size=20`;

      const eventsResponse = await fetch(eventsUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!eventsResponse.ok) {
        throw new Error('Failed to fetch events');
      }

      const eventsData = await eventsResponse.json();
      setRecentEvents(eventsData.events || []);

    } catch (err: any) {
      console.error('Failed to fetch analytics:', err);
      setError(err.message || '加载分析数据失败');
    } finally {
      setLoading(false);
    }
  };

  const getEventTypeLabel = (eventType: string) => {
    const labels: Record<string, string> = {
      'quiz_completed': '問卷完成',
      'product_clicked': '產品點擊',
      'offer_clicked': 'Offer 點擊',
      'purchase_completed': '購買完成',
      'recommendation_generated': '推薦生成',
      'recommendation_viewed': '推薦查看',
      'report_uploaded': '報告上傳',
      'report_extracted': '報告抽取',
      'user_login': '用戶登入',
      'consent_given': '同意授權'
    };
    return labels[eventType] || eventType;
  };

  const getEventTypeColor = (eventType: string) => {
    const colors: Record<string, string> = {
      'quiz_completed': '#10B981',
      'product_clicked': '#3B82F6',
      'offer_clicked': '#8B5CF6',
      'purchase_completed': '#F59E0B',
      'recommendation_generated': '#06B6D4',
      'recommendation_viewed': '#6366F1',
      'report_uploaded': '#EC4899',
      'report_extracted': '#14B8A6',
      'user_login': '#84CC16',
      'consent_given': '#A855F7'
    };
    return colors[eventType] || '#6B7280';
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>加載分析數據中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <p>❌ {error}</p>
          <button onClick={fetchAnalytics} style={styles.retryBtn}>重試</button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>📊 用戶行為分析</h1>
        <button onClick={() => router.push('/admin/dashboard')} style={styles.backBtn}>
          ← 返回儀表板
        </button>
      </div>

      {/* 事件統計摘要 */}
      <div style={styles.summarySection}>
        <h2 style={styles.sectionTitle}>事件統計摘要</h2>
        <div style={styles.summaryGrid}>
          {summary.map((item) => (
            <div
              key={item.event_type}
              style={{
                ...styles.summaryCard,
                borderLeft: `4px solid ${getEventTypeColor(item.event_type)}`
              }}
            >
              <div style={styles.summaryLabel}>{getEventTypeLabel(item.event_type)}</div>
              <div style={styles.summaryCount}>{item.count}</div>
              <div style={styles.summaryDate}>
                最近：{new Date(item.last_at).toLocaleString('zh-TW')}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 事件類型過濾 */}
      <div style={styles.filterSection}>
        <label style={styles.filterLabel}>過濾事件類型：</label>
        <select
          value={selectedEventType}
          onChange={(e) => setSelectedEventType(e.target.value)}
          style={styles.filterSelect}
        >
          <option value="all">全部事件</option>
          <option value="quiz_completed">問卷完成</option>
          <option value="product_clicked">產品點擊</option>
          <option value="offer_clicked">Offer 點擊</option>
          <option value="purchase_completed">購買完成</option>
          <option value="recommendation_generated">推薦生成</option>
          <option value="recommendation_viewed">推薦查看</option>
          <option value="report_uploaded">報告上傳</option>
          <option value="user_login">用戶登入</option>
        </select>
      </div>

      {/* 最近事件列表 */}
      <div style={styles.eventsSection}>
        <h2 style={styles.sectionTitle}>最近事件（最多 20 條）</h2>
        {recentEvents.length === 0 ? (
          <div style={styles.emptyState}>暫無事件記錄</div>
        ) : (
          <div style={styles.eventsList}>
            {recentEvents.map((event) => (
              <div key={event.id} style={styles.eventCard}>
                <div style={styles.eventHeader}>
                  <span
                    style={{
                      ...styles.eventType,
                      background: getEventTypeColor(event.event_type),
                    }}
                  >
                    {getEventTypeLabel(event.event_type)}
                  </span>
                  <span style={styles.eventTime}>
                    {new Date(event.created_at).toLocaleString('zh-TW')}
                  </span>
                </div>
                <div style={styles.eventDetails}>
                  <div style={styles.eventRow}>
                    <span style={styles.eventLabel}>用戶 ID:</span>
                    <span style={styles.eventValue}>{event.user_id.slice(0, 8)}...</span>
                  </div>
                  {event.session_id && (
                    <div style={styles.eventRow}>
                      <span style={styles.eventLabel}>會話 ID:</span>
                      <span style={styles.eventValue}>{event.session_id.slice(0, 8)}...</span>
                    </div>
                  )}
                  {event.ip_address && (
                    <div style={styles.eventRow}>
                      <span style={styles.eventLabel}>IP:</span>
                      <span style={styles.eventValue}>{event.ip_address}</span>
                    </div>
                  )}
                  {event.event_data && Object.keys(event.event_data).length > 0 && (
                    <div style={styles.eventRow}>
                      <span style={styles.eventLabel}>數據:</span>
                      <pre style={styles.eventData}>
                        {JSON.stringify(event.event_data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '24px',
    maxWidth: '1400px',
    margin: '0 auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '32px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#111827',
    margin: 0,
  },
  backBtn: {
    padding: '10px 20px',
    background: '#F3F4F6',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    cursor: 'pointer',
  },
  summarySection: {
    marginBottom: '32px',
  },
  sectionTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#111827',
    marginBottom: '16px',
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '16px',
  },
  summaryCard: {
    background: 'white',
    padding: '20px',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  summaryLabel: {
    fontSize: '14px',
    color: '#6B7280',
    marginBottom: '8px',
  },
  summaryCount: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: '8px',
  },
  summaryDate: {
    fontSize: '12px',
    color: '#9CA3AF',
  },
  filterSection: {
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  filterLabel: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
  },
  filterSelect: {
    padding: '8px 12px',
    border: '1px solid #D1D5DB',
    borderRadius: '8px',
    fontSize: '14px',
    background: 'white',
    cursor: 'pointer',
  },
  eventsSection: {
    marginBottom: '32px',
  },
  eventsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  eventCard: {
    background: 'white',
    padding: '16px',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  eventHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  eventType: {
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '600',
    color: 'white',
  },
  eventTime: {
    fontSize: '12px',
    color: '#6B7280',
  },
  eventDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  eventRow: {
    display: 'flex',
    gap: '8px',
    fontSize: '14px',
  },
  eventLabel: {
    fontWeight: '600',
    color: '#374151',
    minWidth: '80px',
  },
  eventValue: {
    color: '#6B7280',
  },
  eventData: {
    background: '#F9FAFB',
    padding: '8px',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#374151',
    overflow: 'auto',
    maxHeight: '200px',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '400px',
    gap: '16px',
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '4px solid #F3F4F6',
    borderTop: '4px solid #3B82F6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  error: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '400px',
    gap: '16px',
  },
  retryBtn: {
    padding: '10px 20px',
    background: '#3B82F6',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    color: 'white',
    cursor: 'pointer',
  },
  emptyState: {
    textAlign: 'center',
    padding: '48px',
    color: '#9CA3AF',
    fontSize: '16px',
  },
};
