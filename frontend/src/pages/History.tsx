import React, { useEffect, useState } from 'react';
import LottoBall from '../components/LottoBall';
import Card from '../components/Card';
import { fetchDraws } from '../api/client';
import type { LottoDraw } from '../types/lotto';

const PAGE_SIZE = 20;

const History: React.FC = () => {
  const [draws, setDraws] = useState<LottoDraw[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchDraws(page * PAGE_SIZE, PAGE_SIZE);
        setDraws(data.items);
        setTotal(data.total);
      } catch (err) {
        console.error('데이터 로드 실패:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>
        History
      </h1>

      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
            Loading...
          </div>
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr
                  style={{
                    borderBottom: '1px solid #334155',
                    textAlign: 'left',
                  }}
                >
                  <th style={thStyle}>회차</th>
                  <th style={thStyle}>날짜</th>
                  <th style={thStyle}>당첨번호</th>
                  <th style={thStyle}>보너스</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>1등 당첨금</th>
                </tr>
              </thead>
              <tbody>
                {draws.map((draw) => (
                  <tr
                    key={draw.drwNo}
                    style={{ borderBottom: '1px solid #1e293b' }}
                  >
                    <td style={tdStyle}>{draw.drwNo}</td>
                    <td style={tdStyle}>{draw.drwNoDate}</td>
                    <td style={tdStyle}>
                      {draw.numbers.map((n) => (
                        <LottoBall key={n} number={n} size="sm" />
                      ))}
                    </td>
                    <td style={tdStyle}>
                      <LottoBall number={draw.bonusNo} size="sm" isBonus />
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      {(draw.firstWinamnt / 100000000).toFixed(0)}억원
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 12,
                marginTop: 20,
              }}
            >
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                style={btnStyle}
              >
                Prev
              </button>
              <span style={{ color: '#94a3b8', fontSize: 14 }}>
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                style={btnStyle}
              >
                Next
              </button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

const thStyle: React.CSSProperties = {
  padding: '10px 8px',
  fontSize: 13,
  fontWeight: 600,
  color: '#94a3b8',
};

const tdStyle: React.CSSProperties = {
  padding: '10px 8px',
  fontSize: 14,
  verticalAlign: 'middle',
};

const btnStyle: React.CSSProperties = {
  padding: '6px 16px',
  borderRadius: 6,
  border: '1px solid #334155',
  background: '#1e293b',
  color: '#e2e8f0',
  cursor: 'pointer',
  fontSize: 13,
};

export default History;
