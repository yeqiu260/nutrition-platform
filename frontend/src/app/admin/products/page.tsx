'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';

interface Product {
  id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  price: number | null;
  currency: string;
  supplement_id: string;
  purchase_url: string;
  is_active: boolean;
  is_approved: boolean;
  created_at: string;
}

const SUPPLEMENT_OPTIONS = [
  { id: 'vitamin_d', name: '維生素D' },
  { id: 'vitamin_c', name: '維生素C' },
  { id: 'vitamin_b', name: '維生素B群' },
  { id: 'omega3', name: 'Omega-3魚油' },
  { id: 'calcium', name: '鈣' },
  { id: 'magnesium', name: '鎂' },
  { id: 'iron', name: '鐵' },
  { id: 'zinc', name: '鋅' },
  { id: 'probiotics', name: '益生菌' },
  { id: 'collagen', name: '膠原蛋白' },
  { id: 'coq10', name: '輔酶Q10' },
  { id: 'lutein', name: '葉黃素' },
];

export default function ProductsPage() {
  const t = useTranslations('admin');
  const tCommon = useTranslations('common');
  
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [price, setPrice] = useState('');
  const [currency, setCurrency] = useState('TWD');
  const [supplementId, setSupplementId] = useState('');
  const [purchaseUrl, setPurchaseUrl] = useState('');

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('admin_token')}`,
    'Accept-Language': typeof window !== 'undefined' ? localStorage.getItem('NEXT_LOCALE') || 'zh-TW' : 'zh-TW'
  });

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/products/my', { headers: getHeaders() });
      if (res.ok) setProducts(await res.json());
    } catch (err) { console.error('Load error:', err); }
    setLoading(false);
  };

  const showMsg = (msg: string, isError = false) => {
    if (isError) setError(msg); else setMessage(msg);
    setTimeout(() => { setMessage(''); setError(''); }, 3000);
  };

  const resetForm = () => {
    setName(''); setDescription(''); setImageUrl(''); setPrice('');
    setCurrency('TWD'); setSupplementId(''); setPurchaseUrl('');
    setEditingId(null); setShowForm(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      showMsg(tCommon('error'), true);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showMsg(tCommon('error'), true);
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('http://localhost:8000/api/products/upload-image', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_token')}` },
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setImageUrl(data.url);
        showMsg(tCommon('success'));
      } else {
        const err = await res.json();
        showMsg(err.detail || tCommon('error'), true);
      }
    } catch (err: any) {
      showMsg(err.message, true);
    }
    setUploading(false);
  };

  const handleSubmit = async () => {
    if (!name || !supplementId || !purchaseUrl) {
      showMsg(tCommon('error'), true);
      return;
    }
    const body = {
      name, description: description || null, image_url: imageUrl || null,
      price: price ? parseFloat(price) : null, currency, supplement_id: supplementId, purchase_url: purchaseUrl,
    };
    try {
      const url = editingId 
        ? `http://localhost:8000/api/products/my/${editingId}`
        : 'http://localhost:8000/api/products/my';
      const res = await fetch(url, {
        method: editingId ? 'PUT' : 'POST',
        headers: getHeaders(),
        body: JSON.stringify(body),
      });
      if (res.ok) {
        showMsg(tCommon('success'));
        resetForm();
        loadProducts();
      } else {
        const data = await res.json();
        showMsg(data.detail || tCommon('error'), true);
      }
    } catch (err: any) {
      showMsg(err.message, true);
    }
  };

  const handleEdit = (p: Product) => {
    setEditingId(p.id);
    setName(p.name);
    setDescription(p.description || '');
    setImageUrl(p.image_url || '');
    setPrice(p.price?.toString() || '');
    setCurrency(p.currency);
    setSupplementId(p.supplement_id);
    setPurchaseUrl(p.purchase_url);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('forms.delete'))) return;
    try {
      const res = await fetch(`http://localhost:8000/api/products/my/${id}`, {
        method: 'DELETE', headers: getHeaders(),
      });
      if (res.ok) { showMsg(tCommon('success')); loadProducts(); }
    } catch (err: any) { showMsg(err.message, true); }
  };

  const getSupplementName = (id: string) => SUPPLEMENT_OPTIONS.find(s => s.id === id)?.name || id;
  const getImageSrc = (url: string | null) => {
    if (!url) return '';
    if (url.startsWith('/api/')) return `http://localhost:8000${url}`;
    return url;
  };

  if (loading) return <div style={styles.loading}>{tCommon('loading')}</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>{t('products.title')}</h2>
        <button style={styles.addBtn} onClick={() => { resetForm(); setShowForm(true); }}>+ {t('products.add')}</button>
      </div>

      {message && <div style={styles.success}>{message}</div>}
      {error && <div style={styles.error}>{error}</div>}

      {showForm && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>{editingId ? t('products.edit') : t('products.add')}</h3>
          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label style={styles.label}>{t('products.name')}</label>
              <input style={styles.input} value={name} onChange={e => setName(e.target.value)} placeholder={t('products.name')} />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>{t('products.status')}</label>
              <select style={styles.select} value={supplementId} onChange={e => setSupplementId(e.target.value)}>
                <option value="">{t('products.status')}</option>
                {SUPPLEMENT_OPTIONS.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>{t('products.price')}</label>
              <input style={styles.input} type="number" value={price} onChange={e => setPrice(e.target.value)} placeholder="0.00" />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>{tCommon('cancel')}</label>
              <select style={styles.select} value={currency} onChange={e => setCurrency(e.target.value)}>
                <option value="TWD">TWD</option>
                <option value="USD">USD</option>
                <option value="CNY">CNY</option>
              </select>
            </div>
            <div style={{...styles.formGroup, gridColumn: '1 / -1'}}>
              <label style={styles.label}>{t('products.name')}</label>
              <input style={styles.input} value={purchaseUrl} onChange={e => setPurchaseUrl(e.target.value)} placeholder="https://..." />
            </div>
            <div style={{...styles.formGroup, gridColumn: '1 / -1'}}>
              <label style={styles.label}>{t('products.name')}</label>
              <div style={styles.uploadArea}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  style={{ display: 'none' }}
                />
                {imageUrl ? (
                  <div style={styles.previewContainer}>
                    <img src={getImageSrc(imageUrl)} alt="preview" style={styles.previewImg} />
                    <div style={styles.previewActions}>
                      <button type="button" style={styles.changeBtn} onClick={() => fileInputRef.current?.click()}>
                        {t('products.edit')}
                      </button>
                      <button type="button" style={styles.removeBtn} onClick={() => setImageUrl('')}>
                        {t('forms.delete')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    style={styles.uploadBtn}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? tCommon('loading') : '📷 ' + t('products.add')}
                  </button>
                )}
              </div>
            </div>
            <div style={{...styles.formGroup, gridColumn: '1 / -1'}}>
              <label style={styles.label}>{t('products.name')}</label>
              <textarea style={styles.textarea} value={description} onChange={e => setDescription(e.target.value)} placeholder={t('products.name')} rows={3} />
            </div>
          </div>
          <div style={styles.formActions}>
            <button style={styles.cancelBtn} onClick={resetForm}>{tCommon('cancel')}</button>
            <button style={styles.submitBtn} onClick={handleSubmit}>{editingId ? t('products.edit') : t('products.add')}</button>
          </div>
        </div>
      )}

      <div style={styles.card}>
        <h3 style={styles.cardTitle}>{t('products.title')} ({products.length})</h3>
        {products.length === 0 ? (
          <div style={styles.empty}>{tCommon('loading')}</div>
        ) : (
          <div style={styles.productGrid}>
            {products.map(p => (
              <div key={p.id} style={styles.productCard}>
                {p.image_url ? (
                  <img src={getImageSrc(p.image_url)} alt={p.name} style={styles.productImg} />
                ) : (
                  <div style={styles.noImage}>{tCommon('error')}</div>
                )}
                <div style={styles.productInfo}>
                  <h4 style={styles.productName}>{p.name}</h4>
                  <div style={styles.productMeta}>
                    <span style={styles.tag}>{getSupplementName(p.supplement_id)}</span>
                    <span style={p.is_approved ? styles.approved : styles.pending}>
                      {p.is_approved ? tCommon('success') : tCommon('loading')}
                    </span>
                  </div>
                  {p.price && <div style={styles.price}>{p.currency} {p.price.toFixed(2)}</div>}
                  <p style={styles.desc}>{p.description || tCommon('error')}</p>
                  <div style={styles.productActions}>
                    <button style={styles.editBtn} onClick={() => handleEdit(p)}>{t('products.edit')}</button>
                    <button style={styles.deleteBtn} onClick={() => handleDelete(p.id)}>{t('forms.delete')}</button>
                  </div>
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
  container: { padding: '16px' },
  loading: { padding: 50, textAlign: 'center' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 },
  title: { margin: 0, fontSize: 20 },
  addBtn: { padding: '10px 16px', backgroundColor: '#d4a855', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 },
  success: { backgroundColor: '#d4edda', color: '#155724', padding: 12, marginBottom: 16, borderRadius: 4, fontSize: 14 },
  error: { backgroundColor: '#f8d7da', color: '#721c24', padding: 12, marginBottom: 16, borderRadius: 4, fontSize: 14 },
  card: { backgroundColor: '#fff', padding: '16px', borderRadius: 8, marginBottom: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
  cardTitle: { margin: '0 0 16px', fontSize: 16, borderBottom: '1px solid #eee', paddingBottom: 10 },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 },
  formGroup: { display: 'flex', flexDirection: 'column' },
  label: { fontSize: 13, color: '#666', marginBottom: 5 },
  input: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: 4, fontSize: 14, width: '100%', boxSizing: 'border-box' as const },
  select: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: 4, fontSize: 14, width: '100%', boxSizing: 'border-box' as const },
  textarea: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: 4, fontSize: 14, resize: 'vertical' as const, width: '100%', boxSizing: 'border-box' as const },
  formActions: { display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16, flexWrap: 'wrap' as const },
  cancelBtn: { padding: '10px 20px', backgroundColor: '#f5f5f5', color: '#666', border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer' },
  submitBtn: { padding: '10px 20px', backgroundColor: '#d4a855', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' },
  uploadArea: { border: '2px dashed #ddd', borderRadius: 8, padding: 16, textAlign: 'center' as const },
  uploadBtn: { padding: '24px 20px', backgroundColor: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: 8, cursor: 'pointer', fontSize: 14, color: '#666', width: '100%' },
  previewContainer: { display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' as const, justifyContent: 'center' as const },
  previewImg: { width: 100, height: 100, objectFit: 'cover' as const, borderRadius: 8, border: '1px solid #eee' },
  previewActions: { display: 'flex', flexDirection: 'column' as const, gap: 8 },
  changeBtn: { padding: '8px 16px', backgroundColor: '#f5f5f5', border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer', fontSize: 13 },
  removeBtn: { padding: '8px 16px', backgroundColor: '#fff', color: '#e74c3c', border: '1px solid #e74c3c', borderRadius: 4, cursor: 'pointer', fontSize: 13 },
  empty: { padding: 30, textAlign: 'center' as const, color: '#999' },
  productGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16 },
  productCard: { border: '1px solid #eee', borderRadius: 8, overflow: 'hidden' },
  productImg: { width: '100%', height: 140, objectFit: 'cover' as const, backgroundColor: '#f5f5f5' },
  noImage: { width: '100%', height: 140, backgroundColor: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' },
  productInfo: { padding: 12 },
  productName: { margin: '0 0 8px', fontSize: 15 },
  productMeta: { display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' as const },
  tag: { backgroundColor: '#e8f4fd', color: '#1976d2', padding: '2px 6px', borderRadius: 4, fontSize: 11 },
  approved: { backgroundColor: '#d4edda', color: '#155724', padding: '2px 6px', borderRadius: 4, fontSize: 11 },
  pending: { backgroundColor: '#fff3cd', color: '#856404', padding: '2px 6px', borderRadius: 4, fontSize: 11 },
  price: { fontSize: 16, fontWeight: 'bold', color: '#d4a855', marginBottom: 8 },
  desc: { fontSize: 12, color: '#666', margin: '0 0 12px', lineHeight: 1.4 },
  productActions: { display: 'flex', gap: 8 },
  editBtn: { flex: 1, padding: '8px', backgroundColor: '#f5f5f5', border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer', fontSize: 12 },
  deleteBtn: { flex: 1, padding: '8px', backgroundColor: '#fff', color: '#e74c3c', border: '1px solid #e74c3c', borderRadius: 4, cursor: 'pointer', fontSize: 12 },
};
