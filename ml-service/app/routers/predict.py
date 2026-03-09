from fastapi import APIRouter, HTTPException, Query

from app.services import prediction_service

router = APIRouter(prefix="/ml", tags=["예측"])


@router.post("/predict")
async def predict(
    model_type: str = Query(default="lstm"),
    stage: str = Query(default="Production"),
):
    try:
        return await prediction_service.predict_next(model_type, stage)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/predictions")
async def prediction_history(limit: int = Query(default=10, ge=1, le=100)):
    return await prediction_service.get_prediction_history(limit)


@router.get("/models")
async def available_models(stage: str = Query(default="Production")):
    return await prediction_service.get_available_models(stage)
