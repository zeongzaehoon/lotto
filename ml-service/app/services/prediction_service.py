"""예측 서비스 — MLflow Registry에서 모델 로드 → 추론"""

import asyncio
from datetime import datetime, timezone

import numpy as np
import torch

from app.db.mongodb import get_database
from app.services import registry_service

# 모델 캐시: {model_type: {version, model}}
_cache: dict[str, dict] = {}


def _get_model(model_type: str, stage: str = "Production"):
    """Registry에서 모델 로드 (캐싱)"""
    meta = registry_service.get_model_meta(model_type, stage)
    if not meta:
        raise FileNotFoundError(
            f"{stage} 단계에 {model_type} 모델이 없습니다. 학습 후 배포하세요."
        )

    cached = _cache.get(model_type)
    if cached and cached.get("version") == meta["version"]:
        return cached["model"], meta

    model = registry_service.load_model(model_type, stage)
    _cache[model_type] = {"version": meta["version"], "model": model}
    return model, meta


async def predict_next(model_type: str = "lstm", stage: str = "Production") -> dict:
    """다음 회차 예측"""
    if model_type not in registry_service.ALL_MODELS:
        raise ValueError(f"지원하지 않는 모델: {model_type}")

    model, meta = await asyncio.to_thread(_get_model, model_type, stage)
    seq_length = int(meta["params"].get("seq_length", "10"))

    # MongoDB에서 최근 데이터 로드
    db = await get_database()
    cursor = db.draws.find(
        {}, {"numbers": 1, "bonusNo": 1, "drwNo": 1, "_id": 0}
    ).sort("drwNo", -1).limit(seq_length)
    draws = await cursor.to_list(length=seq_length)

    if len(draws) < seq_length:
        raise ValueError(f"데이터 부족: {seq_length}건 필요, {len(draws)}건 존재")
    draws.reverse()

    now = datetime.now(timezone.utc).isoformat()

    if model_type in registry_service.PYTORCH_MODELS:
        vectors = [[v / 45.0 for v in d["numbers"] + [d["bonusNo"]]] for d in draws]
        x = torch.FloatTensor(np.array(vectors)).unsqueeze(0)

        if hasattr(model, 'eval'):
            model.eval()
        with torch.no_grad():
            probs = model(x).squeeze(0).numpy()

        indices = np.argsort(probs)[::-1]
        main_numbers = sorted((indices[:6] + 1).tolist())
        bonus = int(indices[6] + 1)
        confidences = [float(probs[n - 1]) for n in main_numbers]
        bonus_confidence = float(probs[bonus - 1])
    else:
        flat = []
        for d in draws:
            flat.extend(d["numbers"] + [d["bonusNo"]])
        X = np.array([flat], dtype=np.float32)

        # sklearn 모델은 predict 메서드가 다를 수 있음
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(X)[0]
            indices = np.argsort(probs)[::-1]
            main_numbers = sorted((indices[:6] + 1).tolist())
            bonus = int(indices[6] + 1)
            confidences = [float(probs[n - 1]) for n in main_numbers]
            bonus_confidence = float(probs[bonus - 1])
        elif hasattr(model, 'predict'):
            result = model.predict(X)
            if isinstance(result, dict):
                main_numbers = result["numbers"]
                bonus = result["bonusNo"]
                confidences = result.get("confidence", [0.5] * 7)[:6]
                bonus_confidence = confidences[6] if len(result.get("confidence", [])) > 6 else 0.5
            else:
                probs = result[0] if len(result.shape) > 1 else result
                indices = np.argsort(probs)[::-1]
                main_numbers = sorted((indices[:6] + 1).tolist())
                bonus = int(indices[6] + 1)
                confidences = [float(probs[n - 1]) for n in main_numbers]
                bonus_confidence = float(probs[bonus - 1])

    # 데이터 범위
    total_draws = await db.draws.count_documents({})
    oldest = await db.draws.find_one(sort=[("drwNo", 1)], projection={"drwNo": 1})
    latest = await db.draws.find_one(sort=[("drwNo", -1)], projection={"drwNo": 1})

    prediction = {
        "numbers": main_numbers,
        "bonusNo": bonus,
        "confidence": confidences + [bonus_confidence],
        "model_version": f"v{meta['version']} ({stage})",
        "model_type": model_type,
        "created_at": now,
        "total_draws": total_draws,
        "data_range_start": oldest["drwNo"] if oldest else None,
        "data_range_end": latest["drwNo"] if latest else None,
    }

    # 예측 기록 저장
    await db.predictions.insert_one(prediction.copy())

    return prediction


async def get_prediction_history(limit: int = 10) -> list[dict]:
    db = await get_database()
    cursor = db.predictions.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_available_models(stage: str = "Production") -> dict:
    models = await asyncio.to_thread(registry_service.get_available_models, stage)
    return {
        "available_models": [m["model_type"] for m in models],
        "all_models": sorted(registry_service.ALL_MODELS),
        "registry_models": models,
    }
