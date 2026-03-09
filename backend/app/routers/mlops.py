"""MLOps API — ML Service로 프록시"""

import os

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/mlops", tags=["MLOps"])

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8100")


async def _proxy_get(path: str, params: dict | None = None):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{ML_SERVICE_URL}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="ML Service에 연결할 수 없습니다.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.get("/experiments")
async def list_experiments():
    return await _proxy_get("/ml/experiments")


@router.get("/runs")
async def list_runs(
    experiment_name: str = Query(default="lotto-prediction"),
    max_results: int = Query(default=20),
):
    return await _proxy_get("/ml/runs", {"experiment_name": experiment_name, "max_results": max_results})


@router.get("/compare")
async def compare_models(experiment_name: str = Query(default="lotto-prediction")):
    return await _proxy_get("/ml/compare", {"experiment_name": experiment_name})


# Registry 엔드포인트 프록시
@router.get("/registry")
async def registry_models(stage: str = Query(default="Production")):
    return await _proxy_get("/ml/models", {"stage": stage})


@router.get("/registry/{model_name}/versions")
async def model_versions(model_name: str):
    return await _proxy_get(f"/ml/models/{model_name}/versions")


@router.post("/registry/{model_name}/versions/{version}/stage")
async def change_stage(model_name: str, version: int, stage: str = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/ml/models/{model_name}/versions/{version}/stage",
                json={"stage": stage},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="ML Service에 연결할 수 없습니다.")


@router.post("/registry/{model_name}/promote")
async def promote_latest(model_name: str):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{ML_SERVICE_URL}/ml/models/{model_name}/promote-latest")
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="ML Service에 연결할 수 없습니다.")
