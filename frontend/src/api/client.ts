import axios from 'axios';
import type {
  LottoDrawList,
  LottoDraw,
  FrequencyResponse,
  MonthlyStats,
  NumberGap,
  PredictionResult,
  TrainResponse,
  ModelsResponse,
  ModelType,
  CollectionStatus,
} from '../types/lotto';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 120000,
});

// 로또 데이터
export const fetchDraws = async (skip = 0, limit = 20): Promise<LottoDrawList> => {
  const { data } = await api.get('/lotto', { params: { skip, limit } });
  return data;
};

export const fetchLatestDraw = async (): Promise<LottoDraw> => {
  const { data } = await api.get('/lotto/latest');
  return data;
};

export const fetchDraw = async (drawNo: number): Promise<LottoDraw> => {
  const { data } = await api.get(`/lotto/${drawNo}`);
  return data;
};

// 통계
export const fetchFrequency = async (lastN?: number): Promise<FrequencyResponse> => {
  const { data } = await api.get('/stats/frequency', {
    params: lastN ? { last_n: lastN } : {},
  });
  return data;
};

export const fetchMonthlyStats = async (): Promise<MonthlyStats[]> => {
  const { data } = await api.get('/stats/monthly');
  return data;
};

export const fetchNumberGaps = async (): Promise<NumberGap[]> => {
  const { data } = await api.get('/stats/gaps');
  return data;
};

// 예측
export const fetchPrediction = async (
  modelType: ModelType = 'lstm',
): Promise<PredictionResult> => {
  const { data } = await api.post('/predict', null, {
    params: { model_type: modelType },
  });
  return data;
};

export const fetchPredictionHistory = async (
  limit = 10,
): Promise<PredictionResult[]> => {
  const { data } = await api.get('/predictions', { params: { limit } });
  return data;
};

export const fetchAvailableModels = async (): Promise<ModelsResponse> => {
  const { data } = await api.get('/models');
  return data;
};

// 데이터 수집 (Airflow DAG 연동)
export const fetchCollectionStatus = async (): Promise<CollectionStatus> => {
  const { data } = await api.get('/collection/status');
  return data;
};

export const triggerDag = async (dagId: string) => {
  const { data } = await api.post(`/collection/trigger/${dagId}`);
  return data;
};

export const fetchDagStatus = async (dagId: string) => {
  const { data } = await api.get(`/collection/dag-status/${dagId}`);
  return data;
};

export const trainModel = async (
  modelType: ModelType = 'lstm',
  epochs = 100,
  learningRate = 0.001,
  sequenceLength = 10,
  sessionId?: string,
): Promise<TrainResponse> => {
  const { data } = await api.post('/train', {
    model_type: modelType,
    epochs,
    learning_rate: learningRate,
    sequence_length: sequenceLength,
    session_id: sessionId || undefined,
  });
  return data;
};
