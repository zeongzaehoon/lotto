import React, { useState } from 'react';
import { ChevronDown, ChevronUp, X, Terminal } from 'lucide-react';
import LogViewer from './LogViewer';
import type { UseLogStreamReturn } from '../hooks/useLogStream';

interface Props {
  stream: UseLogStreamReturn;
}

const FloatingLogPanel: React.FC<Props> = ({ stream }) => {
  const [collapsed, setCollapsed] = useState(false);

  const hasContent = stream.isConnected || stream.isDone || stream.logs.length > 0;
  if (!hasContent) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: 'var(--bg-surface)',
        borderTop: '1px solid var(--border-default)',
        boxShadow: '0 -4px 24px rgba(0,0,0,0.3)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 16px',
          cursor: 'pointer',
          userSelect: 'none',
        }}
        onClick={() => setCollapsed((v) => !v)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Terminal size={14} color="var(--text-tertiary)" />
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              display: 'inline-block',
              background: stream.isConnected ? 'var(--accent-green)' : stream.isDone ? 'var(--text-tertiary)' : 'var(--accent-red)',
            }}
          />
          <span style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 500 }}>
            {stream.label || 'Log'}
          </span>
          {stream.dagState && (
            <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>
              {stream.dagState}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {stream.isDone && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                stream.clear();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '2px 6px',
                borderRadius: 4,
                border: '1px solid var(--border-default)',
                background: 'transparent',
                color: 'var(--text-tertiary)',
                fontSize: 11,
                cursor: 'pointer',
                gap: 3,
              }}
            >
              <X size={12} /> 닫기
            </button>
          )}
          {collapsed
            ? <ChevronUp size={16} color="var(--text-tertiary)" />
            : <ChevronDown size={16} color="var(--text-tertiary)" />
          }
        </div>
      </div>

      {/* Body */}
      {!collapsed && (
        <div style={{ maxHeight: 280, overflow: 'hidden' }}>
          <LogViewer
            logs={stream.logs}
            dagState={stream.dagState}
            taskStates={stream.taskStates}
            isConnected={stream.isConnected}
            isDone={stream.isDone}
          />
        </div>
      )}
    </div>
  );
};

export default FloatingLogPanel;
