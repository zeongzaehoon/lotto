import React from 'react';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const Card: React.FC<CardProps> = ({ title, children, style }) => {
  return (
    <div
      style={{
        background: '#1e293b',
        borderRadius: 12,
        border: '1px solid #334155',
        padding: 24,
        ...style,
      }}
    >
      {title && (
        <h3
          style={{
            fontSize: 16,
            fontWeight: 600,
            color: '#f1f5f9',
            marginBottom: 16,
          }}
        >
          {title}
        </h3>
      )}
      {children}
    </div>
  );
};

export default Card;
