import React, { useState, useEffect } from 'react';
import { AxiosError } from 'axios';
import { Sparkles } from 'lucide-react';
import LottoBall from '../components/LottoBall';
import Card from '../components/Card';
import { fetchPrediction, fetchAvailableModels, fetchPredictionHistory } from '../api/client';
import type { PredictionResult, ModelType } from '../types/lotto';
import { MODEL_LABELS } from '../types/lotto';

const ALL_MODELS: ModelType[] = ['lstm', 'gru', 'transformer', 'random_forest', 'gradient_boosting'];

const Prediction: React.FC = () => {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [history, setHistory] = useState<PredictionResult[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<ModelType>('lstm');

  useEffect(() => {
    Promise.all([fetchAvailableModels(), fetchPredictionHistory(10)])
      .then(([models, hist]) => {
        setAvailableModels(models.available_models);
        setHistory(hist);
      })
      .catch(() => {});
  }, []);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchPrediction(selectedModel);
      setPrediction(result);
      const hist = await fetchPredictionHistory(10);
      setHistory(hist);
    } catch (err: unknown) {
      const msg = err instanceof AxiosError
        ? (err.response?.data?.detail ?? err.message)
        : err instanceof Error ? err.message : '예측 실패';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '32px 24px', maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24, letterSpacing: '-0.02em' }}>
        번호 예측
      </h2>

      {/* 예측 실행 */}
      <Card title="다음 회차 예측" icon={<Sparkles size={16} />} style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'end', gap: 12 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13, color: 'var(--text-secondary)', flex: 1 }}>
            모델 선택
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as ModelType)}
              style={{
                padding: '10px 14px', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-default)',
                background: 'var(--bg-inset)', color: 'var(--text-primary)', fontSize: 14,
              }}
            >
              {ALL_MODELS.map((m) => (
                <option key={m} value={m} disabled={!availableModels.includes(m)}>
                  {MODEL_LABELS[m]} {availableModels.includes(m) ? '' : '(미학습)'}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={handlePredict}
            disabled={loading || !availableModels.includes(selectedModel)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '10px 28px', borderRadius: 'var(--radius-sm)', border: 'none',
              background: loading || !availableModels.includes(selectedModel)
                ? 'var(--bg-hover)' : 'var(--accent-blue)',
              color: loading || !availableModels.includes(selectedModel)
                ? 'var(--text-tertiary)' : '#fff',
              fontWeight: 600, fontSize: 15, whiteSpace: 'nowrap',
              cursor: loading || !availableModels.includes(selectedModel) ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            <Sparkles size={16} />
            {loading ? '예측 중...' : '예측하기'}
          </button>
        </div>
      </Card>

      {error && (
        <Card style={{ borderColor: 'var(--accent-red)', marginBottom: 24 }}>
          <p style={{ color: 'var(--accent-red)', margin: 0, fontSize: 13 }}>{error}</p>
        </Card>
      )}

      {/* 예측 결과 */}
      {prediction && (
        <Card title="예측 결과" style={{ marginBottom: 24 }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 10, padding: '24px 0', flexWrap: 'wrap',
          }}>
            {prediction.numbers.map((n, i) => (
              <div key={n} style={{ textAlign: 'center' }}>
                <LottoBall number={n} size="lg" />
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                  {((prediction.confidence[i] ?? 0) * 100).toFixed(1)}%
                </div>
              </div>
            ))}
            <span style={{ color: 'var(--text-tertiary)', fontSize: 20, margin: '0 4px' }}>+</span>
            <div style={{ textAlign: 'center' }}>
              <LottoBall number={prediction.bonusNo} size="lg" isBonus />
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                {((prediction.confidence[6] ?? 0) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-tertiary)' }}>
            {MODEL_LABELS[prediction.model_type as ModelType] ?? prediction.model_type} | {prediction.model_version}
            {prediction.data_range_start != null && prediction.data_range_end != null && (
              <> | {prediction.data_range_start}~{prediction.data_range_end}회 데이터 기반</>
            )}
          </div>
        </Card>
      )}

      {/* 예측 히스토리 */}
      {history.length > 0 && (
        <Card title="예측 히스토리">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {history.map((pred, idx) => (
              <div key={idx} style={{
                padding: '10px 14px', background: 'var(--bg-inset)', borderRadius: 'var(--radius-sm)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: 12, color: 'var(--accent-blue)', fontWeight: 600, minWidth: 90,
                  }}>
                    {MODEL_LABELS[pred.model_type as ModelType] ?? pred.model_type}
                  </span>
                  {pred.numbers.map((n) => (
                    <LottoBall key={n} number={n} size="sm" />
                  ))}
                  <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>+</span>
                  <LottoBall number={pred.bonusNo} size="sm" isBonus />
                </div>
                <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 11, color: 'var(--text-tertiary)' }}>
                  {pred.created_at && (
                    <span>{new Date(pred.created_at).toLocaleString('ko-KR')}</span>
                  )}
                  {pred.data_range_start != null && pred.data_range_end != null && (
                    <span>{pred.data_range_start}회 ~ {pred.data_range_end}회 ({pred.total_draws ?? '?'}건)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default Prediction;
