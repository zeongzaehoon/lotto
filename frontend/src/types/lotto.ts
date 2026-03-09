export interface LottoDraw {
  drwNo: number;
  drwNoDate: string;
  numbers: number[];
  bonusNo: number;
  totSellamnt: number;
  firstWinamnt: number;
  firstPrzwnerCo: number;
  firstAccumamnt: number;
}

export interface LottoDrawList {
  total: number;
  items: LottoDraw[];
}

export interface NumberFrequency {
  number: number;
  count: number;
  percentage: number;
}

export interface FrequencyResponse {
  total_draws: number;
  frequencies: NumberFrequency[];
}

export interface MonthlyStats {
  month: number;
  top_numbers: number[];
  draw_count: number;
}

export interface NumberGap {
  number: number;
  last_seen: number;
  gap: number;
}

export interface PredictionResult {
  numbers: number[];
  bonusNo: number;
  confidence: number[];
  model_version: string;
  model_type: string;
  created_at: string;
}

export interface TrainResponse {
  message: string;
  model_type: string;
  epochs: number;
  final_loss: number;
  model_version: string;
}

export interface ModelsResponse {
  available_models: string[];
  all_models: string[];
}

export interface CollectionStatus {
  total_count: number;
  latest_draw_no: number | null;
  oldest_draw_no: number | null;
  latest_draw_date: string | null;
}

export interface CollectionProgress {
  status: 'started' | 'collecting' | 'completed';
  current?: number;
  new_count?: number;
  total?: number;
  existing?: number;
  start_no?: number;
}

export type ModelType =
  | 'lstm'
  | 'gru'
  | 'transformer'
  | 'random_forest'
  | 'gradient_boosting';

export const MODEL_LABELS: Record<ModelType, string> = {
  lstm: 'LSTM',
  gru: 'GRU',
  transformer: 'Transformer',
  random_forest: 'Random Forest',
  gradient_boosting: 'Gradient Boosting',
};
