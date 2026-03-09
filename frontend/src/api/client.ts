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
  CollectionProgress,
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

// 데이터 수집
export const fetchCollectionStatus = async (): Promise<CollectionStatus> => {
  const { data } = await api.get('/collection/status');
  return data;
};

export const startCollection = (
  mode: 'all' | 'latest',
  onProgress: (data: CollectionProgress) => void,
  onError: (error: string) => void,
): (() => void) => {
  const controller = new AbortController();
  const url = `${API_BASE}/api/collection/${mode}`;

  fetch(url, { method: 'POST', signal: controller.signal })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        onError('수집 요청에 실패했습니다.');
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const match = line.match(/^data: (.+)$/m);
          if (match) {
            onProgress(JSON.parse(match[1]));
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message || '수집 중 오류 발생');
      }
    });

  return () => controller.abort();
};

export const trainModel = async (
  modelType: ModelType = 'lstm',
  epochs = 100,
  learningRate = 0.001,
  sequenceLength = 10,
): Promise<TrainResponse> => {
  const { data } = await api.post('/train', {
    model_type: modelType,
    epochs,
    learning_rate: learningRate,
    sequence_length: sequenceLength,
  });
  return data;
};
