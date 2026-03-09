from fastapi import APIRouter, Query

from app.models.lotto import FrequencyResponse, MonthlyStats, NumberGap
from app.services import lotto_service

router = APIRouter(prefix="/api/stats", tags=["통계"])


@router.get("/frequency", response_model=FrequencyResponse)
async def number_frequency(
    last_n: int | None = Query(None, ge=1, description="최근 N회차만 분석"),
):
    """번호별 출현 빈도 분석"""
    return await lotto_service.get_number_frequency(last_n)


@router.get("/monthly", response_model=list[MonthlyStats])
async def monthly_stats():
    """월별 자주 나오는 번호 통계"""
    return await lotto_service.get_monthly_stats()


@router.get("/gaps", response_model=list[NumberGap])
async def number_gaps():
    """각 번호의 미출현 회차 수"""
    return await lotto_service.get_number_gaps()
