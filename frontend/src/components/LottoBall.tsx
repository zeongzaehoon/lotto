import React from 'react';

interface LottoBallProps {
  number: number;
  isBonus?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function getBallColor(num: number): string {
  if (num <= 10) return '#fbbf24';
  if (num <= 20) return '#3b82f6';
  if (num <= 30) return '#ef4444';
  if (num <= 40) return '#6b7280';
  return '#22c55e';
}

const sizes = {
  sm: { width: 32, height: 32, fontSize: 12 },
  md: { width: 42, height: 42, fontSize: 15 },
  lg: { width: 56, height: 56, fontSize: 20 },
};

const LottoBall: React.FC<LottoBallProps> = ({ number, isBonus, size = 'md' }) => {
  const color = getBallColor(number);
  const s = sizes[size];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: s.width,
        height: s.height,
        borderRadius: '50%',
        background: `radial-gradient(circle at 35% 35%, ${color}dd, ${color}88)`,
        color: '#fff',
        fontWeight: 700,
        fontSize: s.fontSize,
        boxShadow: isBonus
          ? `0 0 0 3px #0f172a, 0 0 0 5px ${color}`
          : `0 2px 6px rgba(0,0,0,0.3)`,
        margin: '0 3px',
      }}
    >
      {number}
    </span>
  );
};

export default LottoBall;
