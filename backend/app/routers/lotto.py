from fastapi import APIRouter, HTTPException, Query

from app.services import lotto_service
from app.models.lotto import LottoDrawList, LottoDraw

router = APIRouter(prefix="/api/lotto", tags=["로또 데이터"])


@router.get("", response_model=LottoDrawList)
async def list_draws(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_desc: bool = Query(True),
):
    """전체 추첨 결과 목록 조회"""
    return await lotto_service.get_all_draws(skip, limit, sort_desc)


@router.get("/latest", response_model=LottoDraw)
async def latest_draw():
    """최신 회차 결과 조회"""
    doc = await lotto_service.get_latest_draw()
    if not doc:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return doc


@router.get("/{draw_no}", response_model=LottoDraw)
async def get_draw(draw_no: int):
    """특정 회차 결과 조회"""
    doc = await lotto_service.get_draw_by_no(draw_no)
    if not doc:
        raise HTTPException(status_code=404, detail=f"{draw_no}회차 데이터가 없습니다")
    return doc
