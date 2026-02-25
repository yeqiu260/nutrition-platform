'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';

const navItems = [
  { href: '/admin/dashboard', label: '儀表板', icon: '📊', roles: ['super_admin', 'admin', 'partner'] },
  { href: '/admin/products', label: '商品管理', icon: '📦', roles: ['super_admin', 'admin', 'partner'] },
  { href: '/admin/products/pending', label: '商品審核', icon: '✅', roles: ['super_admin', 'admin'] },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('');
  const [checking, setChecking] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const user = localStorage.getItem('admin_username');
    const r = localStorage.getItem('admin_role');

    if (token) {
      setIsAuthenticated(true);
      setUsername(user || '');
      setRole(r || '');
    } else {
      window.location.href = '/';
      return;
    }
    setChecking(false);

    // 检测屏幕宽度
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) setSidebarOpen(false);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [pathname]);

  // 点击导航后关闭侧边栏（移动端）
  const handleNavClick = () => {
    if (isMobile) setSidebarOpen(false);
  };



  // 检查中
  if (checking) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        載入中...
      </div>
    );
  }

  // 未认证
  if (!isAuthenticated) {
    return null;
  }

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_username');
    localStorage.removeItem('admin_role');
    window.location.href = '/';
  };

  const roleLabels: { [key: string]: string } = {
    super_admin: '超級管理員',
    admin: '管理員',
    partner: '合作商',
    user: '普通用戶',
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* 移动端遮罩 */}
      {isMobile && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 40,
          }}
        />
      )}

      {/* 侧边栏 */}
      <aside
        style={{
          width: 220,
          backgroundColor: '#333',
          color: '#fff',
          position: isMobile ? 'fixed' : 'relative',
          top: 0,
          left: isMobile ? (sidebarOpen ? 0 : -220) : 0,
          height: '100vh',
          zIndex: 50,
          transition: 'left 0.3s ease',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ padding: '20px', borderBottom: '1px solid #444', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 18 }}>管理後台</h1>
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(false)}
              style={{ background: 'none', border: 'none', color: '#fff', fontSize: 24, cursor: 'pointer', padding: 0 }}
            >
              ×
            </button>
          )}
        </div>

        <nav style={{ padding: '15px', flex: 1 }}>
          {navItems
            .filter(item => item.roles.includes(role))
            .map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={handleNavClick}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '12px 15px',
                  marginBottom: 5,
                  borderRadius: 6,
                  textDecoration: 'none',
                  color: pathname === item.href || pathname.startsWith(item.href + '/') ? '#fff' : '#aaa',
                  backgroundColor: pathname === item.href || pathname.startsWith(item.href + '/') ? '#d4a855' : 'transparent',
                }}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
        </nav>

        {/* 用户信息 */}
        <div style={{ padding: 15, borderTop: '1px solid #444' }}>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 14, fontWeight: 'bold' }}>{username}</div>
            <div style={{ fontSize: 12, color: '#888' }}>{roleLabels[role] || role}</div>
          </div>
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '8px',
              backgroundColor: 'transparent',
              color: '#aaa',
              border: '1px solid #555',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            登出
          </button>
        </div>
      </aside>

      {/* 主内容区 */}
      <main style={{ flex: 1, overflow: 'auto', minWidth: 0 }}>
        {/* 移动端顶部栏 */}
        {isMobile && (
          <div
            style={{
              position: 'sticky',
              top: 0,
              backgroundColor: '#333',
              color: '#fff',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              zIndex: 30,
            }}
          >
            <button
              onClick={() => setSidebarOpen(true)}
              style={{
                background: 'none',
                border: 'none',
                color: '#fff',
                fontSize: 24,
                cursor: 'pointer',
                padding: 0,
                lineHeight: 1,
              }}
            >
              ☰
            </button>
            <span style={{ fontSize: 16, fontWeight: 'bold' }}>管理後台</span>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
