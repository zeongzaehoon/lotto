"""통계 API 테스트"""

import pytest


@pytest.mark.asyncio
async def test_frequency(client):
    """번호 빈도 분석 테스트"""
    resp = await client.get("/api/stats/frequency")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_draws" in data
    assert "frequencies" in data
    assert len(data["frequencies"]) == 45


@pytest.mark.asyncio
async def test_frequency_with_last_n(client):
    """최근 N회차 빈도 분석 테스트"""
    resp = await client.get("/api/stats/frequency?last_n=50")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_monthly_stats(client):
    """월별 통계 테스트"""
    resp = await client.get("/api/stats/monthly")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_number_gaps(client):
    """번호 갭 분석 테스트"""
    resp = await client.get("/api/stats/gaps")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
