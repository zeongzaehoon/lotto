"""테스트 공통 설정 및 픽스처"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_draws():
    """테스트용 로또 데이터"""
    return [
        {
            "drwNo": i,
            "drwNoDate": f"2024-01-{i:02d}",
            "numbers": sorted([
                (i * 7 + j) % 45 + 1 for j in range(6)
            ]),
            "bonusNo": (i * 3) % 45 + 1,
            "totSellamnt": 100000000,
            "firstWinamnt": 2000000000,
            "firstPrzwnerCo": 10,
            "firstAccumamnt": 20000000000,
        }
        for i in range(1, 101)
    ]


@pytest.fixture
def mock_db(sample_draws):
    """MongoDB 모킹"""
    mock_collection = MagicMock()

    # find().sort().skip().limit() 체인 모킹
    cursor = AsyncMock()
    cursor.to_list = AsyncMock(return_value=sample_draws[:20])

    find_result = MagicMock()
    find_result.sort = MagicMock(return_value=find_result)
    find_result.skip = MagicMock(return_value=find_result)
    find_result.limit = MagicMock(return_value=cursor)
    find_result.to_list = AsyncMock(return_value=sample_draws)

    mock_collection.find = MagicMock(return_value=find_result)
    mock_collection.find_one = AsyncMock(return_value=sample_draws[0])
    mock_collection.count_documents = AsyncMock(return_value=len(sample_draws))
    mock_collection.insert_one = AsyncMock()

    db = MagicMock()
    db.draws = mock_collection
    db.predictions = MagicMock()
    db.predictions.find = MagicMock(return_value=find_result)
    db.predictions.insert_one = AsyncMock()

    return db


@pytest.fixture
async def client(mock_db):
    """테스트용 HTTP 클라이언트"""
    with patch("app.db.mongodb.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
