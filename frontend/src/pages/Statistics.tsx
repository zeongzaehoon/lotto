import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import Card from '../components/Card';
import LottoBall from '../components/LottoBall';
import { fetchFrequency, fetchMonthlyStats, fetchNumberGaps } from '../api/client';
import type { NumberFrequency, MonthlyStats as MonthlyStatsType, NumberGap } from '../types/lotto';

function getBallColor(num: number): string {
  if (num <= 10) return '#fbbf24';
  if (num <= 20) return '#3b82f6';
  if (num <= 30) return '#ef4444';
  if (num <= 40) return '#6b7280';
  return '#22c55e';
}

const Statistics: React.FC = () => {
  const [frequencies, setFrequencies] = useState<NumberFrequency[]>([]);
  const [monthly, setMonthly] = useState<MonthlyStatsType[]>([]);
  const [gaps, setGaps] = useState<NumberGap[]>([]);
  const [lastN, setLastN] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  // 초기 로드: monthly, gaps (lastN 무관)
  useEffect(() => {
    const loadFixed = async () => {
      try {
        const [monthlyData, gapData] = await Promise.all([
          fetchMonthlyStats(),
          fetchNumberGaps(),
        ]);
        setMonthly(monthlyData);
        setGaps(gapData.slice(0, 15));
      } catch (err) {
        console.error('통계 데이터 로드 실패:', err);
      }
    };
    loadFixed();
  }, []);

  // lastN 변경 시: frequency만 재호출
  useEffect(() => {
    const loadFreq = async () => {
      setLoading(true);
      try {
        const freqData = await fetchFrequency(lastN);
        setFrequencies(
          [...freqData.frequencies].sort((a, b) => a.number - b.number),
        );
      } catch (err) {
        console.error('빈도 데이터 로드 실패:', err);
      } finally {
        setLoading(false);
      }
    };
    loadFreq();
  }, [lastN]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>
        Loading...
      </div>
    );
  }

  const monthNames = [
    '', '1월', '2월', '3월', '4월', '5월', '6월',
    '7월', '8월', '9월', '10월', '11월', '12월',
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>
        Statistics
      </h1>

      {/* 기간 필터 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { label: '전체', value: undefined },
          { label: '최근 50회', value: 50 },
          { label: '최근 100회', value: 100 },
          { label: '최근 200회', value: 200 },
        ].map((opt) => (
          <button
            key={opt.label}
            onClick={() => setLastN(opt.value)}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: '1px solid #334155',
              background: lastN === opt.value ? '#6366f1' : '#1e293b',
              color: lastN === opt.value ? '#fff' : '#94a3b8',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* 출현 빈도 차트 */}
      <Card title="번호별 출현 빈도" style={{ marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={frequencies}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="number"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              interval={0}
            />
            <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
            <Tooltip
              contentStyle={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: 8,
                color: '#e2e8f0',
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {frequencies.map((entry) => (
                <Cell key={entry.number} fill={getBallColor(entry.number)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 미출현 번호 */}
      <Card title="장기 미출현 번호 (Gap)" style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
            gap: 12,
          }}
        >
          {gaps.map((g) => (
            <div
              key={g.number}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: '#0f172a',
                borderRadius: 8,
                padding: '8px 12px',
              }}
            >
              <LottoBall number={g.number} size="sm" />
              <span style={{ color: '#ef4444', fontWeight: 600, fontSize: 14 }}>
                {g.gap}회
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* 월별 통계 */}
      <Card title="월별 자주 나오는 번호">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 12,
          }}
        >
          {monthly.map((m) => (
            <div
              key={m.month}
              style={{
                background: '#0f172a',
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: '#94a3b8',
                  marginBottom: 8,
                }}
              >
                {monthNames[m.month]} ({m.draw_count}회)
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {m.top_numbers.map((n) => (
                  <LottoBall key={n} number={n} size="sm" />
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default Statistics;
