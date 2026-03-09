from collections import Counter

from app.db.mongodb import get_database


async def get_all_draws(skip: int = 0, limit: int = 20, sort_desc: bool = True):
    """전체 추첨 결과 조회"""
    db = await get_database()
    sort_order = -1 if sort_desc else 1
    cursor = db.draws.find(
        {},
        {"_id": 0, "collected_at": 0},
    ).sort("drwNo", sort_order).skip(skip).limit(limit)

    items = await cursor.to_list(length=limit)
    total = await db.draws.count_documents({})
    return {"total": total, "items": items}


async def get_draw_by_no(draw_no: int):
    """특정 회차 결과 조회"""
    db = await get_database()
    doc = await db.draws.find_one(
        {"drwNo": draw_no},
        {"_id": 0, "collected_at": 0},
    )
    return doc


async def get_latest_draw():
    """최신 회차 결과 조회"""
    db = await get_database()
    doc = await db.draws.find_one(
        {},
        {"_id": 0, "collected_at": 0},
        sort=[("drwNo", -1)],
    )
    return doc


async def get_number_frequency(last_n: int | None = None):
    """번호별 출현 빈도 분석"""
    db = await get_database()

    query = {}
    if last_n:
        latest = await db.draws.find_one(sort=[("drwNo", -1)])
        if latest:
            start_no = latest["drwNo"] - last_n + 1
            query = {"drwNo": {"$gte": start_no}}

    cursor = db.draws.find(query, {"numbers": 1, "bonusNo": 1, "_id": 0})
    draws = await cursor.to_list(length=None)

    counter = Counter()
    for draw in draws:
        for num in draw["numbers"]:
            counter[num] += 1
        counter[draw["bonusNo"]] += 1

    total_draws = len(draws)
    frequencies = []
    for num in range(1, 46):
        count = counter.get(num, 0)
        frequencies.append({
            "number": num,
            "count": count,
            "percentage": round(count / max(total_draws * 7, 1) * 100, 2),
        })

    frequencies.sort(key=lambda x: x["count"], reverse=True)
    return {"total_draws": total_draws, "frequencies": frequencies}


async def get_monthly_stats():
    """월별 자주 나오는 번호 통계"""
    db = await get_database()
    cursor = db.draws.find({}, {"drwNoDate": 1, "numbers": 1, "_id": 0})
    draws = await cursor.to_list(length=None)

    monthly: dict[int, Counter] = {}
    monthly_count: dict[int, int] = {}

    for draw in draws:
        month = int(draw["drwNoDate"].split("-")[1])
        if month not in monthly:
            monthly[month] = Counter()
            monthly_count[month] = 0
        monthly_count[month] += 1
        for num in draw["numbers"]:
            monthly[month][num] += 1

    result = []
    for month in range(1, 13):
        if month in monthly:
            top = [num for num, _ in monthly[month].most_common(6)]
            result.append({
                "month": month,
                "top_numbers": top,
                "draw_count": monthly_count[month],
            })

    return result


async def get_number_gaps():
    """각 번호가 마지막으로 출현한 이후 몇 회차가 지났는지"""
    db = await get_database()

    latest = await db.draws.find_one(sort=[("drwNo", -1)])
    if not latest:
        return []

    latest_no = latest["drwNo"]
    cursor = db.draws.find(
        {}, {"drwNo": 1, "numbers": 1, "bonusNo": 1, "_id": 0}
    ).sort("drwNo", -1)
    draws = await cursor.to_list(length=None)

    last_seen = {}
    for draw in draws:
        for num in draw["numbers"]:
            if num not in last_seen:
                last_seen[num] = draw["drwNo"]
        if draw["bonusNo"] not in last_seen:
            last_seen[draw["bonusNo"]] = draw["drwNo"]

    gaps = []
    for num in range(1, 46):
        seen_at = last_seen.get(num, 0)
        gaps.append({
            "number": num,
            "last_seen": seen_at,
            "gap": latest_no - seen_at,
        })

    gaps.sort(key=lambda x: x["gap"], reverse=True)
    return gaps
