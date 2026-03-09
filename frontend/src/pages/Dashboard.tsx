import React, { useEffect, useState } from 'react';
import { Trophy, TrendingUp, Users, Banknote } from 'lucide-react';
import LottoBall from '../components/LottoBall';
import Card from '../components/Card';
import { fetchLatestDraw, fetchFrequency } from '../api/client';
import type { LottoDraw, NumberFrequency } from '../types/lotto';

const Dashboard: React.FC = () => {
  const [latest, setLatest] = useState<LottoDraw | null>(null);
  const [topNumbers, setTopNumbers] = useState<NumberFrequency[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [drawData, freqData] = await Promise.all([
          fetchLatestDraw(),
          fetchFrequency(),
        ]);
        setLatest(drawData);
        setTopNumbers(freqData.frequencies.slice(0, 10));
      } catch {
        // 데이터 없는 초기 상태
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-tertiary)' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>🎱</div>
        <div style={{ fontSize: 14 }}>데이터를 불러오는 중...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '32px 24px', maxWidth: 960, margin: '0 auto' }}>

      {/* 최신 추첨 결과 */}
      {latest && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 20 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>
              {latest.drwNo}회 당첨번호
            </h2>
            <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
              {latest.drwNoDate}
            </span>
          </div>

          <Card>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                padding: '20px 0 24px',
                flexWrap: 'wrap',
              }}
            >
              {latest.numbers.map((n) => (
                <LottoBall key={n} number={n} size="lg" />
              ))}
              <span style={{ color: 'var(--text-tertiary)', fontSize: 20, margin: '0 4px' }}>+</span>
              <LottoBall number={latest.bonusNo} size="lg" isBonus />
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 12,
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: 16,
              }}
            >
              <StatBox
                icon={<Banknote size={16} />}
                label="총 판매금액"
                value={formatKrw(latest.totSellamnt)}
              />
              <StatBox
                icon={<Trophy size={16} />}
                label="1등 당첨금"
                value={formatKrw(latest.firstWinamnt)}
              />
              <StatBox
                icon={<Users size={16} />}
                label="1등 당첨자"
                value={`${latest.firstPrzwnerCo}명`}
              />
            </div>
          </Card>
        </div>
      )}

      {/* TOP 10 빈도 */}
      <Card
        title="역대 출현 빈도 TOP 10"
        icon={<TrendingUp size={16} />}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {topNumbers.map((item, i) => {
            const maxCount = topNumbers[0]?.count || 1;
            return (
              <div
                key={item.number}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <span style={{ fontSize: 12, color: 'var(--text-tertiary)', width: 18, textAlign: 'right' }}>
                  {i + 1}
                </span>
                <LottoBall number={item.number} size="sm" />
                <div
                  style={{
                    flex: 1,
                    height: 6,
                    background: 'var(--bg-inset)',
                    borderRadius: 3,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${(item.count / maxCount) * 100}%`,
                      background: 'linear-gradient(90deg, var(--accent-blue), var(--accent-purple))',
                      borderRadius: 3,
                      transition: 'width 0.6s ease',
                    }}
                  />
                </div>
                <span style={{ color: 'var(--text-secondary)', fontSize: 12, minWidth: 75, textAlign: 'right' }}>
                  {item.count}회 ({item.percentage}%)
                </span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

const StatBox: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({
  icon,
  label,
  value,
}) => (
  <div style={{ padding: '4px 0' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
      <span style={{ color: 'var(--text-tertiary)', display: 'flex' }}>{icon}</span>
      <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{label}</span>
    </div>
    <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
      {value}
    </div>
  </div>
);

function formatKrw(amount: number): string {
  if (amount >= 100000000) return `${(amount / 100000000).toFixed(0)}억원`;
  if (amount >= 10000) return `${(amount / 10000).toFixed(0)}만원`;
  return `${amount.toLocaleString()}원`;
}

export default Dashboard;
