"""데이터 수집 라우터 - 동행복권 API에서 로또 데이터를 수집"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services import collection_service

router = APIRouter(prefix="/api/collection", tags=["수집"])


@router.get("/status")
async def get_status():
    """현재 DB에 저장된 데이터 상태를 반환한다."""
    return await collection_service.get_collection_status()


@router.post("/all")
async def collect_all():
    """전체 회차 데이터를 수집한다. SSE로 진행률을 스트리밍한다."""
    return StreamingResponse(
        collection_service.collect_all(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/latest")
async def collect_latest():
    """최신 회차 데이터만 수집한다. SSE로 진행률을 스트리밍한다."""
    return StreamingResponse(
        collection_service.collect_latest(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
