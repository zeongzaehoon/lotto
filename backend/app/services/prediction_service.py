"""예측 서비스 - 멀티 모델 지원 (LSTM, GRU, Transformer, RF, GBT)"""

import asyncio
import os
import sys
import pickle
from datetime import datetime, timezone

import numpy as np
import torch

ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ml")
sys.path.insert(0, ML_DIR)

from app.db.mongodb import get_database

_model_cache: dict[str, dict] = {}

TORCH_MODELS = {"lstm", "gru", "transformer"}
SKLEARN_MODELS = {"random_forest", "gradient_boosting"}
ALL_MODELS = TORCH_MODELS | SKLEARN_MODELS


def _get_model_path(model_type: str) -> str:
    """모델 파일 경로"""
    if model_type in TORCH_MODELS:
        return os.path.join(ML_DIR, "saved_models", f"lotto_{model_type}.pt")
    return os.path.join(ML_DIR, "saved_models", f"lotto_{model_type}.pkl")


def _load_torch_model(model_type: str):
    """PyTorch 모델 로드 (캐싱)"""
    from model.lstm import LottoLSTM
    from model.gru import LottoGRU
    from model.transformer import LottoTransformer

    model_classes = {"lstm": LottoLSTM, "gru": LottoGRU, "transformer": LottoTransformer}

    model_path = _get_model_path(model_type)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"학습된 {model_type} 모델이 없습니다. 먼저 학습을 실행하세요.")

    mtime = os.path.getmtime(model_path)
    cache_key = model_type
    if _model_cache.get(cache_key, {}).get("mtime") == mtime:
        cached = _model_cache[cache_key]
        return cached["model"], cached["checkpoint"]

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    config = checkpoint["model_config"]
    ModelClass = model_classes[model_type]

    if model_type == "transformer":
        model = ModelClass(
            d_model=config["d_model"],
            nhead=config["nhead"],
            num_layers=config["num_layers"],
        )
    else:
        model = ModelClass(
            hidden_size=config["hidden_size"],
            num_layers=config["num_layers"],
        )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    _model_cache[cache_key] = {"model": model, "checkpoint": checkpoint, "mtime": mtime}
    return model, checkpoint


def _load_sklearn_model(model_type: str):
    """scikit-learn 모델 로드 (캐싱)"""
    model_path = _get_model_path(model_type)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"학습된 {model_type} 모델이 없습니다. 먼저 학습을 실행하세요.")

    mtime = os.path.getmtime(model_path)
    cache_key = model_type
    if _model_cache.get(cache_key, {}).get("mtime") == mtime:
        cached = _model_cache[cache_key]
        return cached["model"], cached["data"]

    with open(model_path, "rb") as f:
        data = pickle.load(f)

    _model_cache[cache_key] = {"model": data["model"], "data": data, "mtime": mtime}
    return data["model"], data


async def _get_draws_sequence(seq_length: int) -> list[dict]:
    """MongoDB에서 최신 시퀀스 로드"""
    db = await get_database()
    cursor = db.draws.find(
        {}, {"numbers": 1, "bonusNo": 1, "_id": 0}
    ).sort("drwNo", -1).limit(seq_length)
    draws = await cursor.to_list(length=seq_length)

    if len(draws) < seq_length:
        raise ValueError(f"데이터 부족: {seq_length}건 필요, {len(draws)}건 존재")

    draws.reverse()
    return draws


async def predict_next(model_type: str = "lstm") -> dict:
    """다음 회차 예측"""
    if model_type not in ALL_MODELS:
        raise ValueError(f"지원하지 않는 모델: {model_type}")

    now = datetime.now(timezone.utc).isoformat()

    if model_type in TORCH_MODELS:
        model, checkpoint = await asyncio.to_thread(_load_torch_model, model_type)
        seq_length = checkpoint["train_config"]["seq_length"]
        draws = await _get_draws_sequence(seq_length)

        vectors = []
        for draw in draws:
            vec = draw["numbers"] + [draw["bonusNo"]]
            vectors.append([v / 45.0 for v in vec])

        x = torch.FloatTensor(np.array(vectors)).unsqueeze(0)
        with torch.no_grad():
            probs = model(x).squeeze(0).numpy()

        indices = np.argsort(probs)[::-1]
        main_numbers = sorted((indices[:6] + 1).tolist())
        bonus = int(indices[6] + 1)
        confidences = [float(probs[n - 1]) for n in main_numbers]
        bonus_confidence = float(probs[bonus - 1])
        version = checkpoint["version"]

    else:
        sk_model, data = await asyncio.to_thread(_load_sklearn_model, model_type)
        seq_length = data["train_config"]["seq_length"]
        draws = await _get_draws_sequence(seq_length)

        flat = []
        for draw in draws:
            flat.extend(draw["numbers"] + [draw["bonusNo"]])
        X = np.array([flat], dtype=np.float32)

        result = sk_model.predict(X)
        main_numbers = result["numbers"]
        bonus = result["bonusNo"]
        confidences = result["confidence"][:6]
        bonus_confidence = result["confidence"][6]
        version = data["version"]

    # 결과 저장
    db = await get_database()
    prediction = {
        "numbers": main_numbers,
        "bonusNo": bonus,
        "confidence": confidences + [bonus_confidence],
        "model_version": version,
        "model_type": model_type,
        "created_at": now,
    }
    await db.predictions.insert_one(prediction.copy())

    return prediction


async def get_prediction_history(limit: int = 10) -> list[dict]:
    """예측 히스토리 조회"""
    db = await get_database()
    cursor = db.predictions.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_available_models() -> list[str]:
    """학습 완료된 모델 목록"""
    available = []
    for mt in ALL_MODELS:
        path = _get_model_path(mt)
        if os.path.exists(path):
            available.append(mt)
    return available


async def train_model(
    model_type: str, epochs: int, learning_rate: float, seq_length: int
) -> dict:
    """모델 학습 (blocking 작업을 thread pool에서 실행)"""
    from train import train as run_train

    result = await asyncio.to_thread(
        run_train,
        model_type=model_type,
        epochs=epochs,
        learning_rate=learning_rate,
        seq_length=seq_length,
    )
    return result
