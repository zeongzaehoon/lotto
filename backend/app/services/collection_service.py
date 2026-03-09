"""로또 데이터 수집 서비스 - 동행복권 API에서 데이터를 가져와 MongoDB에 저장"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

import httpx

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

LOTTO_API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={draw_no}"


async def fetch_single_draw(client: httpx.AsyncClient, draw_no: int) -> dict | None:
    """동행복권 API에서 특정 회차 데이터를 가져온다."""
    url = LOTTO_API_URL.format(draw_no=draw_no)
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("returnValue") == "fail":
            return None
        return {
            "drwNo": data["drwNo"],
            "drwNoDate": data["drwNoDate"],
            "numbers": sorted([
                data["drwtNo1"], data["drwtNo2"], data["drwtNo3"],
                data["drwtNo4"], data["drwtNo5"], data["drwtNo6"],
            ]),
            "bonusNo": data["bnusNo"],
            "totSellamnt": data.get("totSellamnt", 0),
            "firstWinamnt": data.get("firstWinamnt", 0),
            "firstPrzwnerCo": data.get("firstPrzwnerCo", 0),
            "firstAccumamnt": data.get("firstAccumamnt", 0),
            "collected_at": datetime.now(timezone.utc),
        }
    except Exception as e:
        logger.error(f"회차 {draw_no} 데이터 수집 실패: {e}")
        return None


def _sse_event(data: dict) -> str:
    """SSE 형식의 이벤트 문자열을 생성한다."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def collect_all() -> AsyncGenerator[str, None]:
    """전체 회차 데이터를 수집한다. SSE 이벤트로 진행률을 스트리밍한다."""
    db = await get_database()
    collection = db["draws"]

    existing = set()
    async for doc in collection.find({}, {"drwNo": 1}):
        existing.add(doc["drwNo"])

    yield _sse_event({"status": "started", "existing": len(existing)})

    draw_no = 1
    new_count = 0
    consecutive_failures = 0

    async with httpx.AsyncClient() as client:
        while consecutive_failures < 3:
            if draw_no in existing:
                draw_no += 1
                consecutive_failures = 0
                continue

            data = await fetch_single_draw(client, draw_no)
            if data is None:
                consecutive_failures += 1
                draw_no += 1
                continue

            consecutive_failures = 0
            await collection.update_one(
                {"drwNo": data["drwNo"]},
                {"$set": data},
                upsert=True,
            )
            new_count += 1
            draw_no += 1

            if new_count % 5 == 0 or new_count <= 3:
                yield _sse_event({
                    "status": "collecting",
                    "current": draw_no - 1,
                    "new_count": new_count,
                })

            await asyncio.sleep(0.5)

    total = await collection.count_documents({})
    yield _sse_event({
        "status": "completed",
        "new_count": new_count,
        "total": total,
    })


async def collect_latest() -> AsyncGenerator[str, None]:
    """최신 회차만 수집한다. SSE 이벤트로 진행률을 스트리밍한다."""
    db = await get_database()
    collection = db["draws"]

    last_doc = await collection.find_one(sort=[("drwNo", -1)])
    start_no = (last_doc["drwNo"] + 1) if last_doc else 1

    yield _sse_event({"status": "started", "start_no": start_no})

    new_count = 0
    draw_no = start_no
    consecutive_failures = 0

    async with httpx.AsyncClient() as client:
        while consecutive_failures < 3:
            data = await fetch_single_draw(client, draw_no)
            if data is None:
                consecutive_failures += 1
                draw_no += 1
                continue

            consecutive_failures = 0
            await collection.update_one(
                {"drwNo": data["drwNo"]},
                {"$set": data},
                upsert=True,
            )
            new_count += 1
            draw_no += 1

            yield _sse_event({
                "status": "collecting",
                "current": draw_no - 1,
                "new_count": new_count,
            })

            await asyncio.sleep(0.5)

    total = await collection.count_documents({})
    yield _sse_event({
        "status": "completed",
        "new_count": new_count,
        "total": total,
    })


async def get_collection_status() -> dict:
    """현재 DB에 저장된 데이터 상태를 반환한다."""
    db = await get_database()
    collection = db["draws"]

    total = await collection.count_documents({})
    latest = await collection.find_one(sort=[("drwNo", -1)])
    oldest = await collection.find_one(sort=[("drwNo", 1)])

    return {
        "total_count": total,
        "latest_draw_no": latest["drwNo"] if latest else None,
        "oldest_draw_no": oldest["drwNo"] if oldest else None,
        "latest_draw_date": latest.get("drwNoDate") if latest else None,
    }
