import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, History, BarChart3, Sparkles, Cpu, Database } from 'lucide-react';

const navItems = [
  { to: '/', label: '대시보드', icon: LayoutDashboard },
  { to: '/history', label: '추첨 이력', icon: History },
  { to: '/statistics', label: '통계', icon: BarChart3 },
  { to: '/prediction', label: '예측', icon: Sparkles },
  { to: '/training', label: '모델 학습', icon: Cpu },
  { to: '/collection', label: '파이프라인', icon: Database },
];

const Navbar: React.FC = () => {
  return (
    <nav
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        height: 56,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(12px)',
      }}
    >
      <NavLink
        to="/"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginRight: 32,
          textDecoration: 'none',
        }}
      >
        <span style={{ fontSize: 22 }}>🎱</span>
        <span
          style={{
            fontWeight: 700,
            fontSize: 17,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
          }}
        >
          Lotto AI
        </span>
      </NavLink>

      <div style={{ display: 'flex', gap: 2 }}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 14px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 13,
              fontWeight: isActive ? 600 : 400,
              background: isActive ? 'var(--bg-hover)' : 'transparent',
              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              transition: 'all 0.15s ease',
            })}
          >
            <item.icon size={15} strokeWidth={isActive(item.to) ? 2.2 : 1.8} />
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

// NavLink의 isActive를 icon strokeWidth에서 쓸 수 없어서 location 기반으로 체크
function isActive(to: string): boolean {
  if (typeof window === 'undefined') return false;
  const path = window.location.pathname;
  return to === '/' ? path === '/' : path.startsWith(to);
}

export default Navbar;
