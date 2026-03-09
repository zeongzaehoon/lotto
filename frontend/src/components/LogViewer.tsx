import React, { useRef, useEffect } from 'react';
import type { LogMessage } from '../hooks/useLogStream';

interface LogViewerProps {
  logs: LogMessage[];
  dagState: string | null;
  taskStates: Record<string, string>;
  isConnected: boolean;
  isDone: boolean;
}

const TYPE_COLORS: Record<string, string> = {
  airflow_log: 'var(--accent-blue)',
  training_log: 'var(--accent-green)',
};

const TASK_STYLE: Record<string, { bg: string; border: string; color: string }> = {
  success: { bg: '#0d2818', border: 'var(--accent-green)', color: 'var(--accent-green)' },
  running: { bg: '#0d1b2a', border: 'var(--accent-blue)', color: 'var(--accent-blue)' },
  queued:  { bg: '#1a1500', border: 'var(--accent-orange)', color: 'var(--accent-orange)' },
  failed:  { bg: '#200a0a', border: 'var(--accent-red)', color: 'var(--accent-red)' },
  pending: { bg: 'var(--bg-elevated)', border: 'var(--border-default)', color: 'var(--text-tertiary)' },
};

const LogViewer: React.FC<LogViewerProps> = ({ logs, dagState, taskStates, isConnected, isDone }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div style={{
      background: 'var(--bg-inset)',
      borderRadius: 'var(--radius-sm)',
      border: '1px solid var(--border-subtle)',
      fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', monospace",
      fontSize: 12,
      overflow: 'hidden',
    }}>
      {/* Task chips */}
      {Object.keys(taskStates).length > 0 && (
        <div style={{
          padding: '8px 12px',
          display: 'flex',
          gap: 6,
          flexWrap: 'wrap',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-surface)',
        }}>
          {Object.entries(taskStates).map(([taskId, state]) => {
            const s = TASK_STYLE[state] || TASK_STYLE.pending;
            return (
              <span key={taskId} style={{
                padding: '2px 8px', borderRadius: 4, fontSize: 11,
                background: s.bg, border: `1px solid ${s.border}`, color: s.color,
              }}>
                {taskId}: {state}
              </span>
            );
          })}
        </div>
      )}

      {/* Log lines */}
      <div style={{ maxHeight: 320, overflowY: 'auto', padding: '8px 12px' }}>
        {logs.length === 0 && (
          <div style={{ color: 'var(--text-tertiary)', padding: '16px 0', textAlign: 'center' }}>
            {isConnected ? '로그 수신 대기 중...' : '연결 대기 중...'}
          </div>
        )}
        {logs.map((log, i) => {
          const color = TYPE_COLORS[log.type] || 'var(--text-secondary)';
          const text = log.content || log.message || '';
          return text.split('\n').filter(Boolean).map((line, j) => (
            <div key={`${i}-${j}`} style={{ color, lineHeight: 1.7, wordBreak: 'break-all' }}>
              {log.task_id && (
                <span style={{ color: 'var(--text-tertiary)', opacity: 0.7 }}>[{log.task_id}] </span>
              )}
              {line}
            </div>
          ));
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default LogViewer;
