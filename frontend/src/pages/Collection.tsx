import React, { useState, useEffect, useRef } from 'react';
import Card from '../components/Card';
import { fetchCollectionStatus, startCollection } from '../api/client';
import type { CollectionStatus, CollectionProgress } from '../types/lotto';

const Collection: React.FC = () => {
  const [status, setStatus] = useState<CollectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [progress, setProgress] = useState<CollectionProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  const loadStatus = async () => {
    try {
      const data = await fetchCollectionStatus();
      setStatus(data);
    } catch {
      setError('DB 상태를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    return () => cancelRef.current?.();
  }, []);

  const handleCollect = (mode: 'all' | 'latest') => {
    setCollecting(true);
    setProgress(null);
    setError(null);

    const cancel = startCollection(
      mode,
      (data) => {
        setProgress(data);
        if (data.status === 'completed') {
          setCollecting(false);
          loadStatus();
        }
      },
      (err) => {
        setError(err);
        setCollecting(false);
      },
    );
    cancelRef.current = cancel;
  };

  if (loading) {
    return (
      <div style={{ padding: 24, color: '#94a3b8', textAlign: 'center' }}>
        로딩 중...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', marginBottom: 24 }}>
        데이터 수집
      </h2>

      <Card title="현재 DB 상태" style={{ marginBottom: 20 }}>
        {status && status.total_count > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <InfoBox label="총 저장 건수" value={`${status.total_count.toLocaleString()}건`} />
            <InfoBox label="최신 회차" value={`${status.latest_draw_no}회`} />
            <InfoBox label="최초 회차" value={`${status.oldest_draw_no}회`} />
            <InfoBox label="최신 추첨일" value={status.latest_draw_date || '-'} />
          </div>
        ) : (
          <p style={{ color: '#94a3b8', margin: 0 }}>저장된 데이터가 없습니다.</p>
        )}
      </Card>

      <Card title="데이터 수집 실행" style={{ marginBottom: 20 }}>
        <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 16 }}>
          동행복권 API에서 로또 추첨 데이터를 수집합니다. 전체 수집은 약 10분 정도 소요됩니다.
        </p>
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={() => handleCollect('all')}
            disabled={collecting}
            style={{
              padding: '10px 24px',
              borderRadius: 8,
              border: 'none',
              background: collecting ? '#334155' : '#6366f1',
              color: '#fff',
              fontWeight: 600,
              fontSize: 14,
              cursor: collecting ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s',
            }}
          >
            전체 수집
          </button>
          <button
            onClick={() => handleCollect('latest')}
            disabled={collecting}
            style={{
              padding: '10px 24px',
              borderRadius: 8,
              border: '1px solid #6366f1',
              background: collecting ? '#334155' : 'transparent',
              color: collecting ? '#64748b' : '#6366f1',
              fontWeight: 600,
              fontSize: 14,
              cursor: collecting ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            최신 수집
          </button>
        </div>
      </Card>

      {(collecting || progress) && (
        <Card title="수집 진행 상황">
          {progress?.status === 'started' && (
            <p style={{ color: '#94a3b8', margin: 0 }}>수집을 시작합니다...</p>
          )}
          {progress?.status === 'collecting' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: '#94a3b8', fontSize: 14 }}>
                  {progress.current}회차 수집 중...
                </span>
                <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: 14 }}>
                  {progress.new_count}건 수집됨
                </span>
              </div>
              <div
                style={{
                  width: '100%',
                  height: 8,
                  background: '#334155',
                  borderRadius: 4,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    background: '#6366f1',
                    borderRadius: 4,
                    transition: 'width 0.3s',
                    width: `${Math.min(((progress.current || 0) / 1200) * 100, 100)}%`,
                  }}
                />
              </div>
            </div>
          )}
          {progress?.status === 'completed' && (
            <div
              style={{
                padding: 16,
                background: '#064e3b',
                borderRadius: 8,
                border: '1px solid #10b981',
              }}
            >
              <p style={{ color: '#10b981', fontWeight: 600, margin: 0, marginBottom: 4 }}>
                수집 완료
              </p>
              <p style={{ color: '#94a3b8', margin: 0, fontSize: 14 }}>
                신규 {progress.new_count}건 수집 | 총 {progress.total?.toLocaleString()}건 저장됨
              </p>
            </div>
          )}
        </Card>
      )}

      {error && (
        <Card style={{ marginTop: 20, borderColor: '#ef4444' }}>
          <p style={{ color: '#ef4444', margin: 0 }}>{error}</p>
        </Card>
      )}
    </div>
  );
};

const InfoBox: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ background: '#0f172a', borderRadius: 8, padding: 16 }}>
    <div style={{ color: '#64748b', fontSize: 12, marginBottom: 4 }}>{label}</div>
    <div style={{ color: '#f1f5f9', fontSize: 18, fontWeight: 700 }}>{value}</div>
  </div>
);

export default Collection;
