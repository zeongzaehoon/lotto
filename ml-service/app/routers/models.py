"""모델 레지스트리 관리 — 버전 조회, 스테이지 전이"""

import asyncio

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services import registry_service

router = APIRouter(prefix="/ml/models", tags=["Registry"])


class StageRequest(BaseModel):
    stage: str  # "Staging" | "Production" | "Archived"


@router.get("/{model_name}/versions")
async def list_versions(model_name: str):
    versions = await asyncio.to_thread(registry_service.list_versions, model_name)
    return {"model_name": model_name, "versions": versions}


@router.post("/{model_name}/versions/{version}/stage")
async def change_stage(model_name: str, version: int, req: StageRequest):
    try:
        if req.stage == "Production":
            result = await asyncio.to_thread(
                registry_service.promote_to_production, model_name, version
            )
        else:
            result = await asyncio.to_thread(
                registry_service.transition_stage, model_name, version, req.stage
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{model_name}/promote-latest")
async def promote_latest_staging(model_name: str):
    """최신 Staging 버전을 Production으로 승격"""
    versions = await asyncio.to_thread(registry_service.list_versions, model_name)
    staging = [v for v in versions if v["stage"] == "Staging"]
    if not staging:
        raise HTTPException(status_code=404, detail=f"{model_name}에 Staging 모델이 없습니다.")

    latest = max(staging, key=lambda v: v["version"])
    result = await asyncio.to_thread(
        registry_service.promote_to_production, model_name, latest["version"]
    )
    return result
