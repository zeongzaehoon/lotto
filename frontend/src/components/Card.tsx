import React from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const Card: React.FC<CardProps> = ({ title, subtitle, icon, children, style }) => {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        padding: 24,
        ...style,
      }}
    >
      {(title || icon) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          {icon && <span style={{ color: 'var(--text-secondary)', display: 'flex' }}>{icon}</span>}
          <div>
            <h3
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: 'var(--text-primary)',
                letterSpacing: '-0.01em',
                lineHeight: 1.3,
              }}
            >
              {title}
            </h3>
            {subtitle && (
              <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{subtitle}</span>
            )}
          </div>
        </div>
      )}
      {children}
    </div>
  );
};

export default Card;
