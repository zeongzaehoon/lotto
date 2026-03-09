from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.services import training_service

router = APIRouter(prefix="/ml", tags=["학습"])


class TrainRequest(BaseModel):
    model_type: str = "lstm"
    epochs: int = Field(default=100, ge=10, le=500)
    learning_rate: float = Field(default=0.001, gt=0, lt=1)
    sequence_length: int = Field(default=10, ge=5, le=50)
    session_id: str | None = None


@router.post("/train")
async def train_model(req: TrainRequest):
    try:
        result = await training_service.train_model(
            model_type=req.model_type,
            epochs=req.epochs,
            learning_rate=req.learning_rate,
            seq_length=req.sequence_length,
            session_id=req.session_id,
        )
        return {
            "message": "학습 완료",
            "model_type": result["model_type"],
            "epochs": result["epochs"],
            "final_loss": result["final_loss"],
            "model_version": result["version"],
            "registry": result.get("registry"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
