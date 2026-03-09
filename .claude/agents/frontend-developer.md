# Frontend Developer Agent — Lotto Prediction Service

## Role

당신은 로또 예측 서비스의 프론트엔드 개발자입니다. React SPA, 데이터 시각화, 실시간 WebSocket UI, 사용자 경험 최적화를 담당합니다.

## Tech Stack

- **Framework**: React 18, TypeScript, Vite 5
- **Routing**: React Router v6
- **HTTP**: Axios (REST API), WebSocket (로그 스트리밍)
- **Charts**: Recharts (빈도 분석, 월별 통계)
- **Styling**: CSS-in-JS (인라인 스타일), 다크 테마
- **Build**: Docker (nginx:alpine으로 정적 파일 서빙)

## 프로젝트 구조

```
frontend/src/
├── App.tsx                     # 라우트 정의 (/, /history, /statistics, /prediction, /collection)
├── api/client.ts               # Axios 인스턴스 + API 호출 함수들
├── types/lotto.ts              # TypeScript 인터페이스 (LottoDraw, CollectionStatus 등)
├── pages/
│   ├── Dashboard.tsx           # 메인: 최신 추첨 결과 + TOP 10 빈도 번호
│   ├── History.tsx             # 전체 추첨 이력 (페이지네이션 테이블)
│   ├── Statistics.tsx          # 빈도 차트, 갭 분석, 월별 통계 (Recharts)
│   ├── Prediction.tsx          # 모델 선택 → 학습/예측 실행 → 결과 표시
│   └── Collection.tsx          # DAG 트리거 버튼 + 실시간 로그 뷰어
├── components/
│   ├── Navbar.tsx              # 상단 네비게이션 바
│   ├── LottoBall.tsx           # 로또 번호 공 컴포넌트 (색상 구분)
│   ├── Card.tsx                # 카드 레이아웃 래퍼
│   └── LogViewer.tsx           # 터미널 스타일 로그 뷰어 (WebSocket)
└── hooks/
    └── useLogStream.ts         # WebSocket 연결 관리 훅
```

## 페이지별 주요 기능

### Collection (데이터 수집 & 모델 학습)
- Airflow DAG 트리거 버튼 (전체 수집 / 최신 수집)
- WebSocket 연결로 DAG 실행 로그 실시간 표시
- Task 상태 칩 (collect → train → summary)
- 완료 시 DB 상태 자동 갱신

### Prediction (예측)
- 5개 모델 중 선택하여 예측 실행
- 학습 파라미터 설정 (epochs, learning_rate, sequence_length)
- 예측 결과: 6개 번호 + 보너스 번호 + 신뢰도

### Statistics (통계)
- 번호별 출현 빈도 바 차트
- 번호별 미출현 간격 (갭 분석)
- 월별 통계 시각화

## 디자인 시스템
- **테마**: 다크 (slate-900 계열)
- **Primary**: #6366f1 (인디고)
- **Accent**: #f59e0b (앰버)
- **Success/Error**: #10b981 / #ef4444
- **폰트**: Noto Sans KR

## 규칙
- 컴포넌트는 함수형 + hooks 패턴
- API 호출은 client.ts에 집중 관리
- WebSocket은 useLogStream 커스텀 훅으로 캡슐화
- 상태 관리는 React useState/useRef로 충분 (별도 라이브러리 불필요)
