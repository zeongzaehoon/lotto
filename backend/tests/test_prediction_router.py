"""예측 API 테스트"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_predict_no_model(client):
    """학습된 모델 없을 때 404"""
    with patch(
        "app.services.prediction_service._load_torch_model",
        side_effect=FileNotFoundError("모델 없음"),
    ):
        resp = await client.post("/api/predict?model_type=lstm")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_invalid_model(client):
    """잘못된 모델 타입 422"""
    resp = await client.post("/api/predict?model_type=invalid_model")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_available_models(client):
    """사용 가능한 모델 목록 조회"""
    with patch(
        "app.services.prediction_service.get_available_models",
        return_value=["lstm"],
    ):
        resp = await client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "available_models" in data
        assert "all_models" in data


@pytest.mark.asyncio
async def test_train_request_validation(client):
    """학습 요청 파라미터 검증"""
    # epochs 범위 벗어남
    resp = await client.post("/api/train", json={
        "model_type": "lstm",
        "epochs": 5,  # min=10
        "learning_rate": 0.001,
        "sequence_length": 10,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prediction_history(client):
    """예측 히스토리 조회 테스트"""
    resp = await client.get("/api/predictions?limit=5")
    assert resp.status_code == 200
