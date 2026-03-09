from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"


class LottoDraw(BaseModel):
    """로또 추첨 결과 모델"""
    drwNo: int = Field(..., description="회차 번호")
    drwNoDate: str = Field(..., description="추첨일 (YYYY-MM-DD)")
    numbers: list[int] = Field(..., description="당첨번호 6개 (정렬됨)")
    bonusNo: int = Field(..., description="보너스 번호")
    totSellamnt: int = Field(0, description="총 판매금액")
    firstWinamnt: int = Field(0, description="1등 당첨금")
    firstPrzwnerCo: int = Field(0, description="1등 당첨자 수")
    firstAccumamnt: int = Field(0, description="1등 누적 당첨금")


class LottoDrawList(BaseModel):
    total: int
    items: list[LottoDraw]


class NumberFrequency(BaseModel):
    """번호별 출현 빈도"""
    number: int
    count: int
    percentage: float


class FrequencyResponse(BaseModel):
    total_draws: int
    frequencies: list[NumberFrequency]


class MonthlyStats(BaseModel):
    """월별 통계"""
    month: int
    top_numbers: list[int]
    draw_count: int


class NumberGap(BaseModel):
    """번호 미출현 갭"""
    number: int
    last_seen: int
    gap: int


class PredictionResult(BaseModel):
    """예측 결과 모델"""
    numbers: list[int] = Field(..., description="예측 번호 6개")
    bonusNo: int = Field(..., description="예측 보너스 번호")
    confidence: list[float] = Field(..., description="각 번호의 신뢰도")
    model_version: str = Field(..., description="모델 버전")
    model_type: str = Field(default="lstm", description="사용된 모델 타입")
    created_at: str = Field(default="", description="예측 생성 시각 (ISO)")
    total_draws: int | None = Field(default=None, description="학습 데이터 총 건수")
    data_range_start: int | None = Field(default=None, description="데이터 시작 회차")
    data_range_end: int | None = Field(default=None, description="데이터 끝 회차")


class TrainRequest(BaseModel):
    """학습 요청"""
    model_type: ModelType = Field(default=ModelType.LSTM, description="모델 타입")
    epochs: int = Field(default=100, ge=10, le=500)
    learning_rate: float = Field(default=0.001, gt=0, lt=1)
    sequence_length: int = Field(default=10, ge=5, le=50)
    session_id: str | None = Field(default=None, description="WebSocket 로그 세션 ID")


class TrainResponse(BaseModel):
    """학습 결과"""
    message: str
    model_type: str
    epochs: int
    final_loss: float
    model_version: str
