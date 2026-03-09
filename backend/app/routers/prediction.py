from fastapi import APIRouter, HTTPException, Query

from app.models.lotto import (
    ModelType,
    PredictionResult,
    TrainRequest,
    TrainResponse,
)
from app.services import prediction_service

router = APIRouter(prefix="/api", tags=["예측"])


@router.post("/predict", response_model=PredictionResult)
async def predict(
    model_type: ModelType = Query(default=ModelType.LSTM, description="예측 모델 타입"),
):
    """다음 회차 번호 예측"""
    try:
        result = await prediction_service.predict_next(model_type.value)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/predictions", response_model=list[PredictionResult])
async def prediction_history(limit: int = Query(default=10, ge=1, le=100)):
    """예측 히스토리 조회"""
    return await prediction_service.get_prediction_history(limit)


@router.get("/models")
async def available_models():
    """학습 완료된 모델 목록"""
    models = await prediction_service.get_available_models()
    return {"available_models": models, "all_models": [m.value for m in ModelType]}


@router.post("/train", response_model=TrainResponse)
async def train_model(req: TrainRequest):
    """모델 학습 실행"""
    try:
        result = await prediction_service.train_model(
            model_type=req.model_type.value,
            epochs=req.epochs,
            learning_rate=req.learning_rate,
            seq_length=req.sequence_length,
        )
        return {
            "message": "학습 완료",
            "model_type": result["model_type"],
            "epochs": result["epochs"],
            "final_loss": result["final_loss"],
            "model_version": result["version"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
