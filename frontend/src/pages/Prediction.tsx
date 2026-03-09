import React, { useState, useEffect } from 'react';
import { AxiosError } from 'axios';
import LottoBall from '../components/LottoBall';
import Card from '../components/Card';
import {
  fetchPrediction,
  trainModel,
  fetchAvailableModels,
  fetchPredictionHistory,
} from '../api/client';
import type {
  PredictionResult,
  TrainResponse,
  ModelType,
} from '../types/lotto';
import { MODEL_LABELS } from '../types/lotto';

const ALL_MODELS: ModelType[] = [
  'lstm',
  'gru',
  'transformer',
  'random_forest',
  'gradient_boosting',
];

const Prediction: React.FC = () => {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [history, setHistory] = useState<PredictionResult[]>([]);
  const [trainResult, setTrainResult] = useState<TrainResponse | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 모델 선택
  const [selectedModel, setSelectedModel] = useState<ModelType>('lstm');
  const [trainModel_, setTrainModel_] = useState<ModelType>('lstm');

  // 학습 파라미터
  const [epochs, setEpochs] = useState(100);
  const [lr, setLr] = useState(0.001);
  const [seqLen, setSeqLen] = useState(10);

  useEffect(() => {
    const load = async () => {
      try {
        const [models, hist] = await Promise.all([
          fetchAvailableModels(),
          fetchPredictionHistory(5),
        ]);
        setAvailableModels(models.available_models);
        setHistory(hist);
      } catch {
        // 데이터 없는 초기 상태
      }
    };
    load();
  }, []);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchPrediction(selectedModel);
      setPrediction(result);
      const hist = await fetchPredictionHistory(5);
      setHistory(hist);
    } catch (err: unknown) {
      const msg = err instanceof AxiosError
        ? (err.response?.data?.detail ?? err.message)
        : err instanceof Error ? err.message : '예측 실패. 모델이 학습되지 않았을 수 있습니다.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    setError(null);
    setTrainResult(null);
    try {
      const result = await trainModel(trainModel_, epochs, lr, seqLen);
      setTrainResult(result);
      const models = await fetchAvailableModels();
      setAvailableModels(models.available_models);
    } catch (err: unknown) {
      const msg = err instanceof AxiosError
        ? (err.response?.data?.detail ?? err.message)
        : err instanceof Error ? err.message : '학습 실패. 데이터가 충분하지 않을 수 있습니다.';
      setError(msg);
    } finally {
      setTraining(false);
    }
  };

  const isPyTorch = ['lstm', 'gru', 'transformer'].includes(trainModel_);

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>
        Prediction
      </h1>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 24,
          marginBottom: 24,
        }}
      >
        {/* 학습 섹션 */}
        <Card title="Model Training">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <label style={labelStyle}>
              Model Type
              <select
                value={trainModel_}
                onChange={(e) => setTrainModel_(e.target.value as ModelType)}
                style={inputStyle}
              >
                {ALL_MODELS.map((m) => (
                  <option key={m} value={m}>
                    {MODEL_LABELS[m]}
                  </option>
                ))}
              </select>
            </label>

            {isPyTorch && (
              <>
                <label style={labelStyle}>
                  Epochs
                  <input
                    type="number"
                    value={epochs}
                    onChange={(e) => setEpochs(Number(e.target.value))}
                    style={inputStyle}
                    min={10}
                    max={500}
                  />
                </label>
                <label style={labelStyle}>
                  Learning Rate
                  <input
                    type="number"
                    value={lr}
                    onChange={(e) => setLr(Number(e.target.value))}
                    style={inputStyle}
                    step={0.0001}
                    min={0.0001}
                    max={0.1}
                  />
                </label>
              </>
            )}

            <label style={labelStyle}>
              Sequence Length
              <input
                type="number"
                value={seqLen}
                onChange={(e) => setSeqLen(Number(e.target.value))}
                style={inputStyle}
                min={5}
                max={50}
              />
            </label>

            <button
              onClick={handleTrain}
              disabled={training}
              style={{
                ...actionBtnStyle,
                background: training ? '#334155' : '#6366f1',
              }}
            >
              {training ? 'Training...' : `Train ${MODEL_LABELS[trainModel_]}`}
            </button>
          </div>

          {trainResult && (
            <div style={resultBoxStyle}>
              <div style={{ color: '#10b981', fontWeight: 600, marginBottom: 4 }}>
                {trainResult.message}
              </div>
              <div style={{ color: '#94a3b8' }}>
                Model: {trainResult.model_type} | Epochs: {trainResult.epochs} |
                Loss: {trainResult.final_loss.toFixed(6)}
              </div>
            </div>
          )}
        </Card>

        {/* 예측 섹션 */}
        <Card title="Number Prediction">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <label style={labelStyle}>
              Model
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value as ModelType)}
                style={inputStyle}
              >
                {ALL_MODELS.map((m) => (
                  <option key={m} value={m} disabled={!availableModels.includes(m)}>
                    {MODEL_LABELS[m]}{' '}
                    {availableModels.includes(m) ? '' : '(not trained)'}
                  </option>
                ))}
              </select>
            </label>

            <button
              onClick={handlePredict}
              disabled={loading || !availableModels.includes(selectedModel)}
              style={{
                ...actionBtnStyle,
                background:
                  loading || !availableModels.includes(selectedModel)
                    ? '#334155'
                    : '#f59e0b',
                color: '#0f172a',
                fontWeight: 700,
                fontSize: 16,
                padding: '14px 24px',
              }}
            >
              {loading ? 'Predicting...' : 'Predict Next Numbers'}
            </button>
          </div>
        </Card>
      </div>

      {error && (
        <Card style={{ borderColor: '#ef4444', marginBottom: 24 }}>
          <div style={{ color: '#ef4444', fontSize: 14 }}>{error}</div>
        </Card>
      )}

      {prediction && (
        <Card title="Prediction Result" style={{ marginBottom: 24 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
              padding: '24px 0',
              flexWrap: 'wrap',
            }}
          >
            {prediction.numbers.map((n, i) => (
              <div key={n} style={{ textAlign: 'center' }}>
                <LottoBall number={n} size="lg" />
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                  {((prediction.confidence[i] ?? 0) * 100).toFixed(1)}%
                </div>
              </div>
            ))}
            <span style={{ color: '#94a3b8', fontSize: 24, margin: '0 4px' }}>+</span>
            <div style={{ textAlign: 'center' }}>
              <LottoBall number={prediction.bonusNo} size="lg" isBonus />
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                {((prediction.confidence[6] ?? 0) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'center', fontSize: 12, color: '#64748b' }}>
            Model: {MODEL_LABELS[prediction.model_type as ModelType] ?? prediction.model_type} |
            Version: {prediction.model_version}
          </div>
        </Card>
      )}

      {/* 예측 히스토리 */}
      {history.length > 0 && (
        <Card title="Recent Predictions">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {history.map((pred, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  background: '#0f172a',
                  borderRadius: 8,
                  flexWrap: 'wrap',
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    color: '#6366f1',
                    fontWeight: 600,
                    minWidth: 100,
                  }}
                >
                  {MODEL_LABELS[pred.model_type as ModelType] ?? pred.model_type}
                </span>
                {pred.numbers.map((n) => (
                  <LottoBall key={n} number={n} size="sm" />
                ))}
                <span style={{ color: '#94a3b8', fontSize: 12 }}>+</span>
                <LottoBall number={pred.bonusNo} size="sm" isBonus />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  fontSize: 13,
  color: '#94a3b8',
};

const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderRadius: 6,
  border: '1px solid #334155',
  background: '#0f172a',
  color: '#e2e8f0',
  fontSize: 14,
};

const actionBtnStyle: React.CSSProperties = {
  padding: '10px 20px',
  borderRadius: 8,
  border: 'none',
  color: '#fff',
  cursor: 'pointer',
  fontSize: 14,
  transition: 'all 0.2s',
};

const resultBoxStyle: React.CSSProperties = {
  marginTop: 16,
  padding: 12,
  background: '#0f172a',
  borderRadius: 8,
  fontSize: 13,
};

export default Prediction;
