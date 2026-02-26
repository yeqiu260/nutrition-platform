'use client';
import { API_BASE_URL } from '@/lib/api/config';

import { useState, useEffect } from 'react';

interface Product {
  id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  price: number | null;
  currency: string;
  supplement_id: string;
  purchase_url: string;
  partner_name: string | null;
  is_active: boolean;
  is_approved: boolean;
  created_at: string;
}

const SUPPLEMENT_MAP: Record<string, string> = {
  vitamin_d: '維生素D', vitamin_c: '維生素C', vitamin_b: '維生素B群',
  omega3: 'Omega-3魚油', calcium: '鈣', magnesium: '鎂', iron: '鐵',
  zinc: '鋅', probiotics: '益生菌', collagen: '膠原蛋白', coq10: '輔酶Q10', lutein: '葉黃素',
};

export default function PendingProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('admin_token')}`,
  });

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/products/pending`, { headers: getHeaders() });
      if (res.ok) setProducts(await res.json());
    } catch (err) {
      console.error('Load error:', err);
    }
    setLoading(false);
  };

  const showMsg = (msg: string, isError = false) => {
    if (isError) setError(msg); else setMessage(msg);
    setTimeout(() => { setMessage(''); setError(''); }, 3000);
  };

  const handleApprove = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/products/approve/${id}`, {
        method: 'POST', headers: getHeaders(),
      });
      if (res.ok) {
        showMsg('商品已審核通過');
        loadProducts();
      }
    } catch (err: any) {
      showMsg(err.message, true);
    }
  };

  const handleReject = async (id: string) => {
    if (!confirm('確定要拒絕此商品嗎？商品將被刪除。')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/products/reject/${id}`, {
        method: 'POST', headers: getHeaders(),
      });
      if (res.ok) {
        showMsg('商品已拒絕');
        loadProducts();
      }
    } catch (err: any) {
      showMsg(err.message, true);
    }
  };

  const getImageSrc = (url: string | null) => {
    if (!url) return '';
    if (url.startsWith('/api/')) return `http://localhost:8000${url}`;
    return url;
  };

  if (loading) return <div style={styles.loading}>載入中...</div>;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>待審核商品</h2>
      {message && <div style={styles.success}>{message}</div>}
      {error && <div style={styles.error}>{error}</div>}

      {products.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>✓</div>
          <p>目前沒有待審核的商品</p>
        </div>
      ) : (
        <div style={styles.list}>
          {products.map(p => (
            <div key={p.id} style={styles.card}>
              <div style={styles.cardLeft}>
                {p.image_url ? (
                  <img src={getImageSrc(p.image_url)} alt={p.name} style={styles.img} />
                ) : (
                  <div style={styles.noImg}>無圖片</div>
                )}
              </div>
              <div style={styles.cardContent}>
                <h3 style={styles.name}>{p.name}</h3>
                <div style={styles.meta}>
                  <span style={styles.tag}>{SUPPLEMENT_MAP[p.supplement_id] || p.supplement_id}</span>
                  <span style={styles.partner}>合作商: {p.partner_name || '未知'}</span>
                </div>
                {p.price && <div style={styles.price}>{p.currency} {p.price.toFixed(2)}</div>}
                <p style={styles.desc}>{p.description || '無描述'}</p>
                <a href={p.purchase_url} target="_blank" rel="noopener noreferrer" style={styles.link}>
                  查看購買連結 →
                </a>
              </div>
              <div style={styles.cardActions}>
                <button style={styles.approveBtn} onClick={() => handleApprove(p.id)}>✓ 通過</button>
                <button style={styles.rejectBtn} onClick={() => handleReject(p.id)}>✕ 拒絕</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: 30 },
  loading: { padding: 50, textAlign: 'center' },
  title: { margin: '0 0 20px', fontSize: 24 },
  success: { backgroundColor: '#d4edda', color: '#155724', padding: 12, marginBottom: 20, borderRadius: 4 },
  error: { backgroundColor: '#f8d7da', color: '#721c24', padding: 12, marginBottom: 20, borderRadius: 4 },
  empty: { backgroundColor: '#fff', padding: 60, borderRadius: 8, textAlign: 'center', color: '#999' },
  emptyIcon: { fontSize: 48, color: '#52c41a', marginBottom: 15 },
  list: { display: 'flex', flexDirection: 'column', gap: 15 },
  card: { display: 'flex', backgroundColor: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
  cardLeft: { width: 180, flexShrink: 0 },
  img: { width: '100%', height: '100%', objectFit: 'cover', minHeight: 150 },
  noImg: { width: '100%', height: '100%', minHeight: 150, backgroundColor: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' },
  cardContent: { flex: 1, padding: 20 },
  name: { margin: '0 0 10px', fontSize: 18 },
  meta: { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10 },
  tag: { backgroundColor: '#e8f4fd', color: '#1976d2', padding: '3px 10px', borderRadius: 4, fontSize: 12 },
  partner: { color: '#888', fontSize: 13 },
  price: { fontSize: 20, fontWeight: 'bold', color: '#d4a855', marginBottom: 10 },
  desc: { fontSize: 14, color: '#666', margin: '0 0 10px', lineHeight: 1.5 },
  link: { color: '#1976d2', fontSize: 13, textDecoration: 'none' },
  cardActions: { display: 'flex', flexDirection: 'column', gap: 10, padding: 20, borderLeft: '1px solid #eee', justifyContent: 'center' },
  approveBtn: { padding: '12px 24px', backgroundColor: '#52c41a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 },
  rejectBtn: { padding: '12px 24px', backgroundColor: '#fff', color: '#e74c3c', border: '1px solid #e74c3c', borderRadius: 6, cursor: 'pointer', fontSize: 14 },
};
