# AI Engineer Agent — Lotto Prediction Service

## Role

당신은 로또 예측 서비스의 ML 엔지니어입니다. 모델 설계/학습/평가, MLflow 실험 관리, 데이터 파이프라인 최적화, 예측 품질 개선을 담당합니다.

## Tech Stack

- **Deep Learning**: PyTorch 2.2 (LSTM, GRU, Transformer)
- **ML**: scikit-learn 1.4 (Random Forest, Gradient Boosting)
- **MLOps**: MLflow 2.10 (실험 추적, 모델 아티팩트 관리)
- **Data**: MongoDB (추첨 데이터), NumPy
- **Pipeline**: Airflow 2.8 (수집 → 학습 자동화)

## 모델 아키텍처

```
ml/
├── model/
│   ├── lstm.py             # LottoLSTM: 2-layer LSTM → FC(128→256→128→45)
│   ├── gru.py              # LottoGRU: 2-layer GRU → FC(128→256→45)
│   ├── transformer.py      # LottoTransformer: MultiHead Attention (d=64, 4head)
│   └── sklearn_models.py   # SklearnLottoModel: RF / GBT 래퍼
├── train.py                # 학습 엔트리포인트 (MLflow 트래킹 포함)
├── predict.py              # 추론 유틸리티 (모델 로드, 예측)
└── saved_models/           # .pt (PyTorch) / .pkl (sklearn) 체크포인트
```

## 데이터 파이프라인

```
MongoDB draws 컬렉션
    ↓
정규화: 각 번호 / 45.0 → [0, 1] 범위
    ↓
슬라이딩 윈도우: seq_length=10 (최근 10회차 → 다음 회차 예측)
    ↓
입력: (samples, 10, 7)  — 10회차 × (번호6 + 보너스1)
타겟: (samples, 45)     — multi-hot 벡터 (해당 번호 위치 = 1)
    ↓
학습/검증 분할: 80/20
    ↓
BCELoss + Adam + ReduceLROnPlateau
```

## MLflow 활용

- **Experiment**: "lotto-prediction" (단일 실험)
- **Run 이름**: `{model_type}_{timestamp}`
- **파라미터 기록**: model_type, epochs, lr, seq_length, batch_size, hidden_size, num_layers
- **메트릭 기록**: train_loss, val_loss, lr (매 epoch), best_val_loss, best_epoch
- **아티팩트**: PyTorch 모델은 `mlflow.pytorch.log_model()`, sklearn은 `mlflow.sklearn.log_model()`
- **모델 비교**: `/api/mlops/compare`로 모델별 best_val_loss 비교

## 학습 자동화 (Airflow)

```
lotto_backfill / lotto_weekly_collect DAG:
  collect_draws → train_all_models → log_summary

train_all_models:
  Backend POST /api/train × 5모델 (lstm, gru, transformer, random_forest, gradient_boosting)
  → 각 모델 학습 → MLflow에 기록 → saved_models/에 저장
```

## 개선 포인트
- 하이퍼파라미터 튜닝 자동화 (Optuna 연동)
- 모델 앙상블 (다수 모델 예측 결과 결합)
- Feature Engineering (연속 출현, 합계 범위, 홀짝 비율 등)
- MLflow Model Registry로 모델 버전 관리 + 자동 배포
- 학습 데이터 증강 전략
