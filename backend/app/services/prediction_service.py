"""예측 서비스 — ML Service로 프록시"""

import os
import httpx

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8100")


async def predict_next(model_type: str = "lstm") -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{ML_SERVICE_URL}/ml/predict",
            params={"model_type": model_type},
        )
        resp.raise_for_status()
        return resp.json()


async def get_prediction_history(limit: int = 10) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{ML_SERVICE_URL}/ml/predictions",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


async def get_available_models() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{ML_SERVICE_URL}/ml/models")
        resp.raise_for_status()
        return resp.json()


async def train_model(
    model_type: str, epochs: int, learning_rate: float, seq_length: int,
    session_id: str | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            f"{ML_SERVICE_URL}/ml/train",
            json={
                "model_type": model_type,
                "epochs": epochs,
                "learning_rate": learning_rate,
                "sequence_length": seq_length,
                "session_id": session_id,
            },
        )
        resp.raise_for_status()
        return resp.json()
