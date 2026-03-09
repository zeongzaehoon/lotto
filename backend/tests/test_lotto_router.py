"""로또 데이터 API 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_list_draws(client, sample_draws):
    """전체 추첨 결과 목록 조회 테스트"""
    resp = await client.get("/api/lotto?skip=0&limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_list_draws_with_pagination(client):
    """페이지네이션 파라미터 검증"""
    resp = await client.get("/api/lotto?skip=0&limit=5")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_latest_draw(client, sample_draws):
    """최신 회차 조회 테스트"""
    resp = await client.get("/api/lotto/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "drwNo" in data
    assert "numbers" in data
    assert "bonusNo" in data


@pytest.mark.asyncio
async def test_latest_draw_not_found(client, mock_db):
    """데이터 없을 때 404 응답"""
    mock_db.draws.find_one = AsyncMock(return_value=None)
    resp = await client.get("/api/lotto/latest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_draw_by_no(client, sample_draws):
    """특정 회차 조회 테스트"""
    resp = await client.get("/api/lotto/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["drwNo"] == sample_draws[0]["drwNo"]


@pytest.mark.asyncio
async def test_get_draw_not_found(client, mock_db):
    """존재하지 않는 회차 404"""
    mock_db.draws.find_one = AsyncMock(return_value=None)
    resp = await client.get("/api/lotto/99999")
    assert resp.status_code == 404
