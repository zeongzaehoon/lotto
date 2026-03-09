from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPStatusError

from app.models.lotto import (
    ModelType,
    TrainRequest,
)
from app.services import prediction_service

router = APIRouter(prefix="/api", tags=["예측"])


@router.post("/predict")
async def predict(
    model_type: ModelType = Query(default=ModelType.LSTM, description="예측 모델 타입"),
):
    """다음 회차 번호 예측"""
    try:
        return await prediction_service.predict_next(model_type.value)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.get("/predictions")
async def prediction_history(limit: int = Query(default=10, ge=1, le=100)):
    """예측 히스토리 조회"""
    return await prediction_service.get_prediction_history(limit)


@router.get("/models")
async def available_models():
    """학습 완료된 모델 목록 (Registry 기반)"""
    return await prediction_service.get_available_models()


@router.post("/train")
async def train_model(req: TrainRequest):
    """모델 학습 실행"""
    try:
        return await prediction_service.train_model(
            model_type=req.model_type.value,
            epochs=req.epochs,
            learning_rate=req.learning_rate,
            seq_length=req.sequence_length,
            session_id=req.session_id,
        )
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
