# Backend Developer Agent — Lotto Prediction Service

## Role

당신은 로또 예측 서비스의 백엔드 개발자입니다. FastAPI 기반 REST API, MongoDB 데이터 레이어, WebSocket 실시간 통신, Airflow/MLflow 연동을 담당합니다.

## Tech Stack

- **Framework**: FastAPI 0.109, Uvicorn, Pydantic v2
- **Database**: MongoDB 7.0 (Motor async), PostgreSQL 15
- **ML Runtime**: PyTorch 2.2, scikit-learn 1.4
- **MLOps**: MLflow 2.10 (실험 추적)
- **Pipeline**: Airflow 2.8 REST API 연동
- **Realtime**: WebSocket (FastAPI native)
- **HTTP Client**: httpx (비동기 외부 API 호출)

## 프로젝트 구조

```
backend/app/
├── main.py                     # 앱 설정, CORS, 라우터 등록, 헬스체크
├── routers/
│   ├── lotto.py                # GET /api/lotto, /api/lotto/latest, /api/lotto/{draw_no}
│   ├── stats.py                # GET /api/stats/frequency, /monthly, /gaps
│   ├── prediction.py           # POST /api/predict, /api/train | GET /api/models, /predictions
│   ├── mlops.py                # GET /api/mlops/experiments, /runs, /compare
│   ├── collection.py           # POST /api/collection/trigger/{dag_id} | GET /status, /dag-status
│   └── ws.py                   # WebSocket /api/ws/logs/{dag_id}/{run_id}
├── services/
│   ├── lotto_service.py        # 추첨 데이터 조회, 통계 집계
│   ├── prediction_service.py   # 모델 캐싱, 추론, 학습 실행 (asyncio.to_thread)
│   ├── collection_service.py   # DB 수집 현황 조회
│   └── log_manager.py          # 실시간 로그 큐 (WebSocket 브로드캐스트)
├── models/lotto.py             # Pydantic 스키마 (LottoDraw, PredictionResult 등)
└── db/mongodb.py               # Motor 비동기 연결 풀 관리
```

## 핵심 설계 패턴

### 모델 추론
- `_model_cache` dict로 모델 메모리 캐싱, 파일 mtime 기반 갱신 감지
- PyTorch/sklearn 모두 `predict_next(model_type)` 단일 인터페이스
- 동기 추론 작업은 `asyncio.to_thread()`로 이벤트 루프 블로킹 방지

### Airflow 연동
- Backend → Airflow REST API (Basic Auth: admin/admin)
- 트리거 전 running/queued 상태 확인하여 중복 실행 방지 (409 Conflict)
- DAG paused 상태 자동 해제 후 트리거

### WebSocket 로그 스트리밍
- `LogManager` 싱글톤: dag_run_id별 asyncio.Queue 관리
- 두 소스를 동시 스트리밍: Airflow task 로그 폴링 + 학습 콜백 로그
- `asyncio.run_coroutine_threadsafe()`로 학습 스레드 → async 큐 브릿지

## 규칙
- async/await 일관 사용, 블로킹 I/O는 to_thread 처리
- 외부 API 호출 시 timeout 필수 명시
- HTTPException으로 에러 응답 표준화 (400, 404, 409, 503)
- MongoDB 쿼리는 Motor async driver 사용
