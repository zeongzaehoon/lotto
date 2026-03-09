# Lotto Prediction Service

딥러닝 기반 로또 번호 예측 서비스. 데이터 수집부터 예측까지의 전체 ML 파이프라인을 구축한 프로젝트입니다.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (port 80)                       │
│              Reverse Proxy / Entry Point                 │
├────────┬────────┬──────────┬────────────┘
│        │        │          │
│   /    │ /api/  │ /airflow │ /mlflow
│        │        │          │
▼        ▼        ▼          ▼
React    FastAPI  Airflow    MLflow
:80      :8000    :8080      :5000
         │
         ├── MongoDB (데이터 저장)
         └── ML Models (PyTorch / scikit-learn)
```

## Tech Stack

| 영역 | 기술 |
|------|------|
| Data Pipeline | Apache Airflow |
| Database | MongoDB |
| Backend API | FastAPI + Motor (async) |
| Deep Learning | PyTorch (LSTM, GRU, Transformer) |
| Machine Learning | scikit-learn (Random Forest, Gradient Boosting) |
| MLOps | MLflow (experiment tracking) |
| Frontend | React + TypeScript + Recharts |
| Infra | Docker Compose + Nginx |

## Project Structure

```
lotto_pytorch/
├── docker-compose.yml
├── .env
│
├── nginx/                      # Reverse Proxy
│   ├── Dockerfile
│   └── nginx.conf
│
├── airflow/                    # 데이터 수집 파이프라인
│   ├── Dockerfile
│   └── dags/
│       └── lotto_collect_dag.py    # backfill + weekly DAG
│
├── backend/                    # FastAPI 백엔드
│   ├── Dockerfile
│   ├── tests/                      # pytest 테스트
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db/mongodb.py
│       ├── models/lotto.py         # Pydantic 스키마
│       ├── routers/
│       │   ├── lotto.py            # 데이터 CRUD
│       │   ├── stats.py            # 통계 분석
│       │   ├── prediction.py       # 예측/학습
│       │   └── mlops.py            # MLflow 연동
│       └── services/
│           ├── lotto_service.py
│           └── prediction_service.py
│
├── ml/                         # ML 모델
│   ├── tests/                      # 모델 단위 테스트
│   ├── model/
│   │   ├── lstm.py                 # LSTM
│   │   ├── gru.py                  # GRU
│   │   ├── transformer.py         # Transformer
│   │   └── sklearn_models.py      # RF, GBT
│   ├── train.py                    # 통합 학습 (MLflow 트래킹)
│   ├── predict.py                  # 통합 예측
│   └── saved_models/
│
├── mlflow/                     # MLflow 서버
│   ├── Dockerfile
│   └── entrypoint.sh
│
├── frontend/                   # React SPA
│   ├── Dockerfile
│   └── src/
│       ├── api/client.ts
│       ├── types/lotto.ts
│       ├── components/
│       │   ├── LottoBall.tsx
│       │   ├── Navbar.tsx
│       │   └── Card.tsx
│       └── pages/
│           ├── Dashboard.tsx       # 최신 결과 + 빈도 TOP 10
│           ├── History.tsx         # 전체 이력 (페이지네이션)
│           ├── Statistics.tsx      # 빈도 차트 + 갭 + 월별
│           └── Prediction.tsx      # 모델 학습/예측
│
└── mongo-init/init.js          # DB 초기화
```

## Quick Start

```bash
# 1. 전체 서비스 실행
docker compose up -d --build

# 2. 서비스 확인
#    Frontend:  http://localhost
#    API Docs:  http://localhost/docs
#    Airflow:   http://localhost/airflow  (admin / admin)
#    MLflow:    http://localhost/mlflow

# 3. 초기 데이터 수집
#    Airflow UI에서 'lotto_backfill' DAG를 수동 트리거
#    → 1회차부터 최신 회차까지 전체 데이터 수집

# 4. 모델 학습 & 예측
#    Frontend Prediction 페이지에서 모델 선택 → Train → Predict
```

## API Endpoints

### 로또 데이터

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lotto` | 전체 추첨 결과 (페이지네이션) |
| GET | `/api/lotto/latest` | 최신 회차 결과 |
| GET | `/api/lotto/{draw_no}` | 특정 회차 결과 |

### 통계

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stats/frequency` | 번호별 출현 빈도 (전체/최근N) |
| GET | `/api/stats/monthly` | 월별 자주 나오는 번호 |
| GET | `/api/stats/gaps` | 번호별 미출현 회차 수 |

### 예측 & 학습

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/predict?model_type=lstm` | 다음 회차 예측 |
| POST | `/api/train` | 모델 학습 실행 |
| GET | `/api/predictions` | 예측 히스토리 |
| GET | `/api/models` | 학습된 모델 목록 |

### MLOps

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/mlops/experiments` | MLflow 실험 목록 |
| GET | `/api/mlops/runs` | 학습 실행 기록 |
| GET | `/api/mlops/compare` | 모델 성능 비교 |

## Prediction Models

| Model | Type | Description |
|-------|------|-------------|
| **LSTM** | PyTorch | 2-layer LSTM, 시퀀스 패턴 학습 |
| **GRU** | PyTorch | LSTM보다 빠른 학습, 유사 성능 |
| **Transformer** | PyTorch | Self-attention 기반 장기 의존성 포착 |
| **Random Forest** | scikit-learn | 앙상블 기반 번호 출현 확률 예측 |
| **Gradient Boosting** | scikit-learn | 부스팅 기반 순차적 학습 |

모든 모델은 동일한 인터페이스를 통해:
- 과거 N회차 시퀀스를 입력받아
- 45개 번호 각각의 출현 확률을 출력하고
- 상위 6개를 당첨번호, 7번째를 보너스로 선택

## Data Pipeline

```
동행복권 API  →  Airflow DAG  →  MongoDB  →  FastAPI  →  React
                  │                                        │
                  ├── backfill (수동, 전체 회차)             │
                  └── weekly (자동, 매주 일요일 03:00)       │
                                                           │
                  Train  →  MLflow (tracking)              │
                    │                                      │
                    └──→  saved_models/  →  Predict  ──────┘
```

## Testing

```bash
# 백엔드 API 테스트
cd backend && pip install -r requirements.txt && pytest -v

# ML 모델 테스트
cd ml && pip install -r requirements.txt && pytest -v
```

## ML 프로세스 학습 가이드

이 프로젝트의 ML 코드를 읽으며 PyTorch 기초를 학습할 수 있습니다.
아래 순서대로 파일을 읽으면 자연스럽게 전체 파이프라인을 이해할 수 있습니다.

### 읽는 순서

```
1. ml/model/lstm.py          ← 모델 구조 (가장 기본)
2. ml/model/gru.py           ← LSTM과 비교하며 이해
3. ml/model/transformer.py   ← Self-Attention 개념
4. ml/train.py               ← 학습 루프 (핵심!)
5. ml/predict.py             ← 추론 과정
```

### 1단계: 데이터 준비 (train.py)

```
MongoDB에서 로또 당첨 데이터 가져오기
    ↓
정규화: 각 번호를 45로 나눔 (0~1 범위)
    예) [3, 11, 15, 29, 35, 44, 7] → [0.067, 0.244, 0.333, ...]
    ↓
슬라이딩 윈도우로 시퀀스 생성:
    X[0] = [1회차, 2회차, ..., 10회차]  →  y[0] = 11회차 (정답)
    X[1] = [2회차, 3회차, ..., 11회차]  →  y[1] = 12회차 (정답)
    ...
    ↓
타겟(y)은 Multi-Hot Encoding으로 변환:
    [3, 11, 15, 29, 35, 44, 7] → [0,0,1,0,...,1,...,1,...] (45차원, 해당 번호만 1)
    ↓
DataLoader로 배치(batch) 단위로 묶기:
    32개씩 묶어서 모델에 전달 (메모리 효율 + 학습 안정성)
```

### 2단계: 모델 구조 (model/*.py)

모든 모델은 동일한 인터페이스를 따릅니다:

```
입력: (batch, seq_length, 7)    ← 과거 N회차의 번호 시퀀스
출력: (batch, 45)               ← 45개 번호 각각의 출현 확률 (0~1)
```

#### LSTM (lstm.py) - 순차 기억 모델
```
입력 (batch, 10, 7)
    ↓
LSTM 2층: 시퀀스를 순서대로 읽으며 패턴 학습
  - hidden_size=128: 내부 기억 벡터 크기
  - 게이트 3개 (forget, input, output)로 무엇을 기억/삭제할지 결정
    ↓
마지막 시점의 출력만 사용 (batch, 128)
    ↓
FC 네트워크: 128 → 256 → 128 → 45 → Sigmoid
```

#### GRU (gru.py) - LSTM의 경량 버전
```
LSTM과 동일한 구조, 게이트 2개 (reset, update)
파라미터가 ~75% 수준으로 적고 학습이 빠름
FC 네트워크도 한 층 적음: 128 → 256 → 45
```

#### Transformer (transformer.py) - 어텐션 기반 모델
```
입력 (batch, 10, 7)
    ↓
입력 투영: 7차원 → 64차원 (d_model) + √d_model 스케일링
    ↓
위치 인코딩(Positional Encoding): sin/cos로 순서 정보 주입
    ↓
Transformer Encoder (Self-Attention):
  "10회차 전 데이터"와 "2회차 전 데이터" 중 뭐가 더 중요한지 학습
  - 모든 시점을 동시에 비교 (LSTM처럼 순차 처리 X)
  - nhead=4: 4가지 관점에서 병렬로 어텐션 계산
    ↓
마지막 시점 출력 (batch, 64)
    ↓
FC: 64 → 128 → 45 → Sigmoid
```

### 3단계: 학습 루프 (train.py)

```python
# 핵심 학습 루프 요약 (의사코드)
for epoch in range(100):       # 전체 데이터를 100번 반복
    model.train()              # 학습 모드 (Dropout 활성화)

    for batch_X, batch_y in dataloader:
        # 1) 이전 그래디언트 초기화
        optimizer.zero_grad()

        # 2) 순전파: 입력 → 모델 → 예측
        predictions = model(batch_X)

        # 3) 손실 계산: 예측과 정답의 차이
        loss = BCELoss(predictions, batch_y)

        # 4) 역전파: 손실에서 각 가중치의 기여도 계산
        loss.backward()

        # 5) 가중치 업데이트: 기여도 방향으로 조금씩 조정
        optimizer.step()

    # 검증: 학습에 안 쓴 데이터로 실제 성능 확인
    model.eval()               # 평가 모드 (Dropout 비활성화)
    with torch.no_grad():      # 그래디언트 계산 끄기 (메모리 절약)
        val_loss = evaluate(model, val_data)
```

#### 핵심 개념 정리

| 개념 | 설명 | 코드 위치 |
|------|------|-----------|
| **nn.Module** | 모든 PyTorch 모델의 부모 클래스 | lstm.py:27 |
| **forward()** | 데이터가 모델을 통과하는 경로 정의 | lstm.py:90 |
| **state_dict** | 모델의 모든 가중치를 담은 딕셔너리 | train.py (저장), predict.py (로드) |
| **DataLoader** | 데이터를 배치 단위로 나눠주는 도구 | train.py |
| **BCELoss** | Binary Cross Entropy. 확률 예측의 오차 측정 | train.py |
| **optimizer.zero_grad()** | 이전 배치의 그래디언트 초기화 | train.py |
| **loss.backward()** | 역전파로 그래디언트 계산 | train.py |
| **optimizer.step()** | 그래디언트 방향으로 가중치 업데이트 | train.py |
| **model.train()** | 학습 모드 (Dropout ON) | train.py |
| **model.eval()** | 평가 모드 (Dropout OFF) | train.py, predict.py |
| **torch.no_grad()** | 그래디언트 계산 비활성화 (추론 시) | predict.py |
| **register_buffer** | 학습 안 되는 텐서를 모델에 등록 | transformer.py:71 |
| **PositionalEncoding** | Transformer에 순서 정보를 주입 | transformer.py:27 |

### 4단계: 추론 (predict.py)

```
저장된 모델 파일 로드 (.pt)
    ↓
torch.load() → 체크포인트 딕셔너리
    ↓
빈 모델 생성 → load_state_dict()로 가중치 주입
    ↓
model.eval() → 추론 모드 전환
    ↓
MongoDB에서 최신 N회차 데이터 로드
    ↓
정규화 → 텐서 변환 → unsqueeze(0)으로 배치 차원 추가
    ↓
torch.no_grad() 블록 안에서 model(x) 실행
    ↓
출력 (45,): 각 번호의 확률
    ↓
np.argsort()로 확률 높은 순서 정렬
    ↓
상위 6개 = 본번호, 7번째 = 보너스
```

### 5단계: MLflow 트래킹 (train.py)

```
학습 시작 시:
    mlflow.start_run()
    mlflow.log_params({...})   ← 하이퍼파라미터 기록
    ↓
학습 완료 후:
    mlflow.log_metrics({...})  ← 손실값, 정확도 기록
    mlflow.pytorch.log_model() ← 모델 아티팩트 저장
    ↓
MLflow UI (/mlflow)에서:
    실험별 비교, 하이퍼파라미터 최적화 등 가능
```

### PyTorch vs scikit-learn 비교

| 항목 | PyTorch | scikit-learn |
|------|---------|--------------|
| 모델 정의 | nn.Module 상속, forward() 구현 | 제공되는 클래스 사용 |
| 학습 | 직접 루프 작성 (zero_grad → forward → backward → step) | model.fit(X, y) 한 줄 |
| 추론 | model.eval() + torch.no_grad() | model.predict(X) |
| 저장 | torch.save(state_dict) → .pt | pickle.dump() → .pkl |
| 로드 | 모델 구조 재생성 + load_state_dict() | pickle.load()로 바로 사용 |
| GPU 지원 | model.to("cuda") | 기본 미지원 |
| 입력 형태 | 3D 텐서 (batch, seq, features) | 2D 배열 (samples, features) |
| 장점 | 유연한 커스터마이징, GPU 가속 | 간단, 빠른 프로토타이핑 |

## Services & Ports

| Service | Internal | External (via Nginx) |
|---------|----------|---------------------|
| Nginx | :80 | http://localhost |
| Frontend | :80 | http://localhost/ |
| Backend | :8000 | http://localhost/api/ |
| Airflow | :8080 | http://localhost/airflow/ |
| MLflow | :5000 | http://localhost/mlflow/ |
| MongoDB | :27017 | localhost:27017 |
| PostgreSQL | :5432 | (internal only) |
