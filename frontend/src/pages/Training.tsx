import React, { useState, useEffect } from 'react';
import { AxiosError } from 'axios';
import { Cpu, Play, CheckCircle2 } from 'lucide-react';
import Card from '../components/Card';
import { trainModel, fetchAvailableModels } from '../api/client';
import type { TrainResponse, ModelType } from '../types/lotto';
import { MODEL_LABELS } from '../types/lotto';
import { useGlobalLogStream } from '../App';

const ALL_MODELS: ModelType[] = ['lstm', 'gru', 'transformer', 'random_forest', 'gradient_boosting'];

const Training: React.FC = () => {
  const [trainResult, setTrainResult] = useState<TrainResponse | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedModel, setSelectedModel] = useState<ModelType>('lstm');
  const [epochs, setEpochs] = useState(100);
  const [lr, setLr] = useState(0.001);
  const [seqLen, setSeqLen] = useState(10);

  const logStream = useGlobalLogStream();

  useEffect(() => {
    fetchAvailableModels()
      .then((m) => setAvailableModels(m.available_models))
      .catch(() => {});
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    setError(null);
    setTrainResult(null);

    const sessionId = `train_${Date.now()}`;
    logStream.connectTrain(sessionId, `${MODEL_LABELS[selectedModel]} 학습`);

    try {
      const result = await trainModel(selectedModel, epochs, lr, seqLen, sessionId);
      setTrainResult(result);
      const models = await fetchAvailableModels();
      setAvailableModels(models.available_models);
    } catch (err: unknown) {
      const msg = err instanceof AxiosError
        ? (err.response?.data?.detail ?? err.message)
        : err instanceof Error ? err.message : '학습 실패';
      setError(msg);
    } finally {
      setTraining(false);
    }
  };

  const isPyTorch = ['lstm', 'gru', 'transformer'].includes(selectedModel);

  return (
    <div style={{ padding: '32px 24px', maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24, letterSpacing: '-0.02em' }}>
        모델 학습
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        {/* 학습 설정 */}
        <Card title="학습 설정" icon={<Cpu size={16} />}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label style={labelStyle}>
              모델 타입
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value as ModelType)}
                style={inputStyle}
              >
                {ALL_MODELS.map((m) => (
                  <option key={m} value={m}>{MODEL_LABELS[m]}</option>
                ))}
              </select>
            </label>

            {isPyTorch && (
              <>
                <label style={labelStyle}>
                  Epochs
                  <input type="number" value={epochs} onChange={(e) => setEpochs(Number(e.target.value))}
                    style={inputStyle} min={10} max={500} />
                </label>
                <label style={labelStyle}>
                  Learning Rate
                  <input type="number" value={lr} onChange={(e) => setLr(Number(e.target.value))}
                    style={inputStyle} step={0.0001} min={0.0001} max={0.1} />
                </label>
              </>
            )}

            <label style={labelStyle}>
              Sequence Length
              <input type="number" value={seqLen} onChange={(e) => setSeqLen(Number(e.target.value))}
                style={inputStyle} min={5} max={50} />
            </label>

            <button
              onClick={handleTrain}
              disabled={training}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '10px 20px', borderRadius: 'var(--radius-sm)', border: 'none',
                background: training ? 'var(--bg-hover)' : 'var(--accent-blue)',
                color: training ? 'var(--text-tertiary)' : '#fff',
                fontWeight: 600, fontSize: 14,
                cursor: training ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <Play size={14} />
              {training ? '학습 중...' : `${MODEL_LABELS[selectedModel]} 학습 시작`}
            </button>
          </div>

          {trainResult && (
            <div style={{
              marginTop: 16, padding: 14, borderRadius: 'var(--radius-sm)',
              background: '#0d2818', border: '1px solid var(--accent-green)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--accent-green)', fontWeight: 600, marginBottom: 6 }}>
                <CheckCircle2 size={14} /> {trainResult.message}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                {trainResult.model_type} | Epochs: {trainResult.epochs} | Loss: {trainResult.final_loss.toFixed(6)}
              </div>
            </div>
          )}
        </Card>

        {/* 모델 현황 */}
        <Card title="등록된 모델" icon={<CheckCircle2 size={16} />}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {ALL_MODELS.map((m) => {
              const available = availableModels.includes(m);
              return (
                <div key={m} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-inset)',
                }}>
                  <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    {MODEL_LABELS[m]}
                  </span>
                  <span style={{
                    padding: '2px 10px', borderRadius: 4, fontSize: 12, fontWeight: 500,
                    background: available ? '#0d2818' : 'var(--bg-elevated)',
                    color: available ? 'var(--accent-green)' : 'var(--text-tertiary)',
                    border: `1px solid ${available ? 'var(--accent-green)' : 'var(--border-default)'}22`,
                  }}>
                    {available ? 'Production' : '미학습'}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {error && (
        <Card style={{ borderColor: 'var(--accent-red)' }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
        </Card>
      )}
    </div>
  );
};

const labelStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 6,
  fontSize: 13, color: 'var(--text-secondary)',
};

const inputStyle: React.CSSProperties = {
  padding: '8px 12px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--border-default)',
  background: 'var(--bg-inset)', color: 'var(--text-primary)', fontSize: 14,
};

export default Training;
