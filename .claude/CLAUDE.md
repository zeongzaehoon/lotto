# Lotto Prediction Service — CLAUDE.md

## 프로젝트 개요

딥러닝 기반 로또 번호 예측 서비스. Docker Compose 10개 컨테이너로 구성된 풀스택 MLOps 파이프라인.

## 기술 스택

- **Frontend**: React 18, TypeScript, Vite, Recharts, Lucide Icons, Pretendard
- **Backend (API Gateway)**: FastAPI, httpx (ML Service 프록시), WebSocket 릴레이
- **ML Service**: FastAPI, PyTorch 2.2, scikit-learn 1.4, MLflow 2.10 Model Registry
- **Pipeline**: Airflow 2.8 (수집 → 학습 → Registry 배포)
- **Database**: MongoDB 7.0 (Motor async), PostgreSQL 15
- **Infra**: Docker Compose, Nginx

## 서비스 구조

```
Nginx (:4567)
  ├→ /api/        → Backend (:8000) → ML Service (:8100)
  ├→ /airflow/    → Airflow (:8080)
  ├→ /mlflow/     → MLflow (:5000)
  └→ /            → Frontend (:80)
```

## 디렉토리 구조

```
frontend/src/pages/     — Dashboard, History, Statistics, Prediction, Training, Collection
backend/app/routers/    — lotto, stats, prediction, mlops, collection, ws
ml-service/app/         — predict, train, models, mlops, ws + registry_service
ml/model/               — LSTM, GRU, Transformer, sklearn 모델 정의
airflow/dags/           — lotto_collect_dag.py (수집→학습→승격→요약)
```

---

## Agent 협업 워크플로우

기능 요청이나 큰 변경사항이 있을 때 아래 4단계 프로세스를 따릅니다.

### Phase 1: 계획 (Plan)

**주도**: product-strategist + 전체 agent

1. 요구사항을 분석하고 각 agent가 자기 관점에서 의견을 제시
2. product-strategist가 우선순위와 스코프를 정리
3. ai-engineer가 기술적 실현 가능성과 아키텍처 방향 제시
4. 결과물: **구현 계획** (무엇을, 왜, 어떤 순서로)

```
[사용자 요청]
  → product-strategist: 왜 필요한가? 우선순위는?
  → ai-engineer: 기술적으로 어떻게? 아키텍처 영향은?
  → backend-developer: API/서비스 변경점은?
  → frontend-developer: UI 변경점은?
  → designer: 디자인 트렌드 리서치 필요한가?
  → qa-engineer: 테스트 관점에서 리스크는?
```

### Phase 2: 설계 (Design)

**주도**: 해당 도메인 agent

1. backend-developer: API 스펙, 서비스 구조, DB 스키마 설계
2. ai-engineer: 모델/파이프라인/Registry 설계
3. frontend-developer: 컴포넌트 구조, 페이지 흐름 설계
4. designer: WebSearch로 트렌드 리서치 → 폰트/아이콘/색상 선정
5. 결과물: **파일별 변경 계획** (어떤 파일을 어떻게)

### Phase 3: 구현 (Build)

**주도**: 각 도메인 agent 병렬 작업

우선순위 순서:
1. **인프라**: docker-compose.yml, Dockerfile, nginx.conf
2. **백엔드/ML**: 서비스 코드, 라우터, DB 스키마
3. **프론트엔드**: 페이지, 컴포넌트, API 클라이언트
4. **파이프라인**: Airflow DAG

규칙:
- 기존 파일 수정 우선, 새 파일은 최소화
- CSS 변수(`var(--*)`) 사용, 하드코딩 색상 금지
- Backend은 경량 프록시 유지, ML 로직은 ml-service에
- 타입은 `types/lotto.ts` ↔ `models/lotto.py` 동기화

### Phase 4: 검증 (Test)

**주도**: qa-engineer

**중요: 모든 테스트와 검증은 Docker 컨테이너 내부에서 실행합니다.**
- 로컬 환경에는 PyTorch, MLflow 등 ML 의존성이 없음
- API 테스트: `docker exec lotto-backend` 또는 `curl http://localhost:4567/api/...`
- ML 테스트: `docker exec lotto-ml-service python3 -c "..."`
- DB 확인: `docker exec lotto-mongodb mongosh ...`
- Airflow 확인: `docker exec lotto-airflow-webserver airflow ...`

```
검증 순서:
1. 컨테이너 빌드:    docker compose up -d --build
2. 상태 확인:        docker compose ps (모든 서비스 healthy/running)
3. 헬스체크:         curl localhost:4567/api/health
                     docker exec lotto-ml-service curl localhost:8100/ml/health
4. API 테스트:       curl localhost:4567/api/models
                     curl -X POST localhost:4567/api/predict?model_type=lstm
5. ML 검증:          docker exec lotto-ml-service python3 -c "import mlflow; ..."
6. DB 검증:          docker exec lotto-mongodb mongosh -u admin -p ... --eval "db.draws.countDocuments({})"
7. 로그 확인:        docker compose logs {service} --tail 20
```

```
체크리스트:
  □ docker compose ps — 모든 컨테이너 정상
  □ /api/health — 200 OK
  □ /ml/health — 200 OK
  □ 프론트 페이지 렌더링
  □ 핵심 기능 동작 (예측, 학습, 수집)
  □ 에러 로그 없음
```

### Phase 5: 문서 동기화 (Sync Docs)

**필수: 모든 작업 완료 후 반드시 수행합니다.**

코드가 변경되면 아래 문서들이 실제 구현과 일치하는지 확인하고, 다르면 수정합니다.

| 파일 | 확인 항목 |
|------|----------|
| `README.md` | 아키텍처 다이어그램, 서비스 목록, API 엔드포인트, 디렉토리 구조, Tech Stack |
| `.claude/CLAUDE.md` | 서비스 구조, 디렉토리 구조, 코딩 규칙, 자주 쓰는 명령 |
| `.claude/agents/backend-developer.md` | 라우터/서비스 목록, 프록시 패턴, 의존성 |
| `.claude/agents/frontend-developer.md` | 페이지/컴포넌트 목록, 라우트 경로, 훅 |
| `.claude/agents/ai-engineer.md` | 모델 목록, Registry 이름, 파이프라인 흐름 |
| `.claude/agents/designer.md` | CSS 변수, 색상 팔레트, 컴포넌트 체계 |
| `.claude/agents/qa-engineer.md` | 테스트 명령, 엔드포인트 목록, 체크리스트 |
| `.claude/agents/product-strategist.md` | 기능 우선순위 (P0/P1/P2), 기술 어필 포인트 |
| `.claude/agents/brand-marketer.md` | 포지셔닝, Tech Stack 시각화, 데모 시나리오 |

```
확인 방법:
  1. 새 API가 추가되었는가? → README.md API 표 + qa-engineer.md 테스트 명령
  2. 새 컨테이너가 추가되었는가? → README.md 서비스 표 + CLAUDE.md 서비스 구조
  3. 새 페이지/컴포넌트가 추가되었는가? → frontend-developer.md + designer.md
  4. ML 모델/파이프라인이 변경되었는가? → ai-engineer.md + README.md ML 섹션
  5. 디자인이 변경되었는가? → designer.md CSS 변수/컴포넌트 체계
```

---

## Agent별 담당 영역

| Agent | 파일 범위 | 핵심 역할 |
|-------|----------|----------|
| **product-strategist** | — | 기능 우선순위, 스코프, WHY 판단 |
| **ai-engineer** | `ml/`, `ml-service/` | 모델, 학습, Registry, MLflow |
| **backend-developer** | `backend/` | API 게이트웨이, 프록시, WebSocket |
| **frontend-developer** | `frontend/` | React 페이지, 컴포넌트, 훅 |
| **designer** | `frontend/`, `index.html`, `index.css` | 디자인 시스템, 트렌드 리서치, 에셋 |
| **qa-engineer** | 전체 | 검증, 에러 확인, 엣지 케이스 |
| **brand-marketer** | `README.md`, `.claude/agents/` | 포트폴리오 메시지, 기술 어필 |

## 코딩 규칙

### 공통
- 한국어 주석/로그, 영문 코드
- 에러 메시지는 사용자에게 한국어로

### Backend
- async/await 일관 사용
- ML 로직 직접 import 금지 → ML Service httpx 프록시
- HTTPException으로 에러 표준화

### ML Service
- MLflow Model Registry로 모델 버전 관리
- 학습 완료 → Staging 등록 → promote로 Production 승격
- 예측 시 Production 모델만 로드

### Frontend
- CSS 변수 사용 (`var(--bg-surface)` 등)
- Lucide React 아이콘 사용
- 글로벌 상태는 App 레벨 Context (useGlobalLogStream 등)
- API 호출은 `api/client.ts`에 집중

### Airflow DAG
- 수집 → 학습 → 승격 → 요약 4단계
- Backend API 경유 (직접 ML Service 호출 X)
- 실패 허용 (consecutive_failures 카운트)

## 자주 쓰는 명령

```bash
docker compose up -d                    # 전체 서비스 시작
docker compose up -d --build frontend   # 프론트만 재빌드
docker compose up -d --build ml-service # ML 서비스만 재빌드
docker compose logs {service} --tail 30 # 로그 확인
docker compose ps                       # 상태 확인
```
