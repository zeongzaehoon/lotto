import React from 'react';

interface LottoBallProps {
  number: number;
  isBonus?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

// 동행복권 공식 색상 기준
function getBallColor(num: number): [string, string] {
  if (num <= 10) return ['#fbc400', '#e5a800']; // 노랑
  if (num <= 20) return ['#69c8f2', '#4ba8d9']; // 파랑
  if (num <= 30) return ['#ff7272', '#e85555']; // 빨강
  if (num <= 40) return ['#aaa', '#888'];        // 회색
  return ['#b0d840', '#95bc2e'];                  // 초록
}

const sizes = {
  sm: { width: 28, height: 28, fontSize: 11 },
  md: { width: 40, height: 40, fontSize: 14 },
  lg: { width: 52, height: 52, fontSize: 19 },
};

const LottoBall: React.FC<LottoBallProps> = ({ number, isBonus, size = 'md' }) => {
  const [light, dark] = getBallColor(number);
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
        background: `linear-gradient(135deg, ${light} 0%, ${dark} 100%)`,
        color: '#fff',
        fontWeight: 700,
        fontSize: s.fontSize,
        lineHeight: 1,
        textShadow: '0 1px 2px rgba(0,0,0,0.2)',
        boxShadow: isBonus
          ? `0 0 0 2px var(--bg-surface), 0 0 0 4px ${light}`
          : '0 1px 3px rgba(0,0,0,0.3)',
        margin: '0 2px',
        flexShrink: 0,
      }}
    >
      {number}
    </span>
  );
};

export default LottoBall;
