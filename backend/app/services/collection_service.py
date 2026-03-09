"""로또 데이터 수집 상태 서비스 - 수집은 Airflow DAG에서 수행"""

from app.db.mongodb import get_database


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
