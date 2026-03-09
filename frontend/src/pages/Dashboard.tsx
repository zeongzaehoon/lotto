import React, { useEffect, useState } from 'react';
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
      } catch (err) {
        console.error('데이터 로드 실패:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>
        Dashboard
      </h1>

      {latest && (
        <Card title={`${latest.drwNo}회 (${latest.drwNoDate})`} style={{ marginBottom: 24 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexWrap: 'wrap',
            }}
          >
            {latest.numbers.map((n) => (
              <LottoBall key={n} number={n} size="lg" />
            ))}
            <span style={{ color: '#94a3b8', fontSize: 24, margin: '0 8px' }}>
              +
            </span>
            <LottoBall number={latest.bonusNo} size="lg" isBonus />
          </div>
          <div
            style={{
              marginTop: 16,
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 12,
            }}
          >
            <InfoBox
              label="총 판매금액"
              value={`${(latest.totSellamnt / 100000000).toFixed(0)}억원`}
            />
            <InfoBox
              label="1등 당첨금"
              value={`${(latest.firstWinamnt / 100000000).toFixed(0)}억원`}
            />
            <InfoBox
              label="1등 당첨자"
              value={`${latest.firstPrzwnerCo}명`}
            />
          </div>
        </Card>
      )}

      <Card title="역대 출현 빈도 TOP 10">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {topNumbers.map((item) => (
            <div
              key={item.number}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
              }}
            >
              <LottoBall number={item.number} size="sm" />
              <div
                style={{
                  flex: 1,
                  height: 20,
                  background: '#0f172a',
                  borderRadius: 10,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(item.percentage * 5, 100)}%`,
                    background: 'linear-gradient(90deg, #6366f1, #818cf8)',
                    borderRadius: 10,
                    transition: 'width 0.5s',
                  }}
                />
              </div>
              <span style={{ color: '#94a3b8', fontSize: 13, minWidth: 60 }}>
                {item.count}회 ({item.percentage}%)
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

const InfoBox: React.FC<{ label: string; value: string }> = ({
  label,
  value,
}) => (
  <div
    style={{
      background: '#0f172a',
      borderRadius: 8,
      padding: '12px 16px',
    }}
  >
    <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
      {label}
    </div>
    <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>
      {value}
    </div>
  </div>
);

export default Dashboard;
