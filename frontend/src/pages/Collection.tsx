import React, { useState, useEffect, useRef } from 'react';
import { Database, Play, RefreshCw, CheckCircle2, Clock, XCircle, HardDriveDownload } from 'lucide-react';
import Card from '../components/Card';
import { fetchCollectionStatus, triggerDag, fetchDagStatus } from '../api/client';
import { useGlobalLogStream } from '../App';
import type { CollectionStatus } from '../types/lotto';

interface DagState {
  state: string | null;
  dag_run_id?: string;
  end_date?: string;
  message?: string;
}

const DAG_LABELS: Record<string, { title: string; description: string; icon: React.ReactNode }> = {
  lotto_backfill: {
    title: '전체 수집 + 모델 학습',
    description: '1회차부터 전체 데이터를 수집하고 모델을 학습합니다.',
    icon: <HardDriveDownload size={16} />,
  },
  lotto_weekly_collect: {
    title: '최신 수집 + 모델 갱신',
    description: '최신 데이터를 수집하고 모델을 재학습합니다.',
    icon: <RefreshCw size={16} />,
  },
};

const STATE_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  success: { label: '완료', color: 'var(--accent-green)', bg: '#0d2818', icon: <CheckCircle2 size={13} /> },
  running: { label: '실행 중', color: 'var(--accent-blue)', bg: '#0d1b2a', icon: <RefreshCw size={13} /> },
  queued:  { label: '대기 중', color: 'var(--accent-orange)', bg: '#1a1500', icon: <Clock size={13} /> },
  failed:  { label: '실패', color: 'var(--accent-red)', bg: '#200a0a', icon: <XCircle size={13} /> },
};

const Collection: React.FC = () => {
  const [status, setStatus] = useState<CollectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dagStates, setDagStates] = useState<Record<string, DagState>>({});
  const [triggering, setTriggering] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<Record<string, number>>({});
  const logStream = useGlobalLogStream();

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
    Object.keys(DAG_LABELS).forEach((dagId) => {
      fetchDagStatus(dagId)
        .then((data) => setDagStates((prev) => ({ ...prev, [dagId]: data })))
        .catch(() => {});
    });
    return () => { Object.values(pollingRef.current).forEach(clearTimeout); };
  }, []);

  useEffect(() => {
    if (logStream.isDone) {
      loadStatus();
      Object.keys(DAG_LABELS).forEach((dagId) => {
        fetchDagStatus(dagId)
          .then((data) => setDagStates((prev) => ({ ...prev, [dagId]: data })))
          .catch(() => {});
      });
    }
  }, [logStream.isDone]);

  const handleTrigger = async (dagId: string) => {
    setTriggering(dagId);
    setError(null);
    try {
      const resp = await triggerDag(dagId);
      setDagStates((prev) => ({ ...prev, [dagId]: { state: 'queued', dag_run_id: resp.dag_run_id } }));
      logStream.connectDag(dagId, resp.dag_run_id, DAG_LABELS[dagId]?.title || dagId);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'DAG 트리거에 실패했습니다.');
    } finally {
      setTriggering(null);
    }
  };

  const isRunning = (dagId: string) => {
    const s = dagStates[dagId]?.state;
    return s === 'running' || s === 'queued';
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-tertiary)', fontSize: 14 }}>
        데이터를 불러오는 중...
      </div>
    );
  }

  return (
    <div style={{ padding: '32px 24px', maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24, letterSpacing: '-0.02em' }}>
        파이프라인
      </h2>

      {/* DB 상태 */}
      <Card title="데이터 현황" icon={<Database size={16} />} style={{ marginBottom: 20 }}>
        {status && status.total_count > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            <MetricBox label="총 건수" value={`${status.total_count.toLocaleString()}`} />
            <MetricBox label="최신 회차" value={`${status.latest_draw_no}회`} />
            <MetricBox label="최초 회차" value={`${status.oldest_draw_no}회`} />
            <MetricBox label="최신 추첨일" value={status.latest_draw_date || '-'} />
          </div>
        ) : (
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>저장된 데이터가 없습니다.</p>
        )}
      </Card>

      {/* DAG 트리거 */}
      {Object.entries(DAG_LABELS).map(([dagId, { title, description, icon }]) => {
        const dagState = dagStates[dagId];
        const running = isRunning(dagId);
        const stateConf = dagState?.state ? STATE_CONFIG[dagState.state] : null;

        return (
          <Card key={dagId} title={title} icon={icon} style={{ marginBottom: 16 }}>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 14 }}>
              {description}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                onClick={() => handleTrigger(dagId)}
                disabled={running || triggering === dagId}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 18px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  background: running || triggering === dagId ? 'var(--bg-hover)' : 'var(--accent-blue)',
                  color: running || triggering === dagId ? 'var(--text-tertiary)' : '#fff',
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: running || triggering === dagId ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <Play size={14} />
                {triggering === dagId ? '트리거 중...' : running ? '실행 중...' : '실행'}
              </button>

              {stateConf && (
                <span style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                  background: stateConf.bg, color: stateConf.color,
                  border: `1px solid ${stateConf.color}22`,
                }}>
                  {stateConf.icon} {stateConf.label}
                </span>
              )}
            </div>

            {dagState?.end_date && dagState.state === 'success' && (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 12, marginTop: 10, marginBottom: 0 }}>
                마지막 완료: {new Date(dagState.end_date).toLocaleString('ko-KR')}
              </p>
            )}
          </Card>
        );
      })}

      {error && (
        <Card style={{ borderColor: 'var(--accent-red)' }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
        </Card>
      )}
    </div>
  );
};

const MetricBox: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ background: 'var(--bg-inset)', borderRadius: 'var(--radius-sm)', padding: '12px 14px' }}>
    <div style={{ color: 'var(--text-tertiary)', fontSize: 11, marginBottom: 4 }}>{label}</div>
    <div style={{ color: 'var(--text-primary)', fontSize: 16, fontWeight: 700, letterSpacing: '-0.02em' }}>{value}</div>
  </div>
);

export default Collection;
