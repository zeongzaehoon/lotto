"""
로또 번호 데이터 수집 DAG

- 초기 실행 시 1회차부터 전체 데이터를 수집 (backfill)
- 이후 매주 일요일 새벽에 최신 회차 데이터를 추가 수집
"""

import os
import time
import logging
from datetime import datetime, timedelta, timezone

import requests
from pymongo import MongoClient
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

LOTTO_API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={draw_no}"


def get_mongo_client():
    """MongoDB 클라이언트 생성. MONGODB_URL 환경변수 필수."""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL 환경변수가 설정되지 않았습니다.")
    return MongoClient(mongodb_url)


def _get_db_name() -> str:
    return os.getenv("MONGO_DB_NAME", "lotto_db")


def fetch_single_draw(draw_no: int) -> dict | None:
    """동행복권 API에서 특정 회차 데이터를 가져온다."""
    url = LOTTO_API_URL.format(draw_no=draw_no)
    try:
        resp = requests.get(url, timeout=10)
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


def collect_all_draws(**kwargs):
    """전체 회차 데이터를 수집한다. 이미 존재하는 회차는 건너뛴다."""
    client = get_mongo_client()
    try:
        db = client[_get_db_name()]
        collection = db["draws"]

        existing = set(
            doc["drwNo"] for doc in collection.find({}, {"drwNo": 1})
        )
        logger.info(f"기존 데이터: {len(existing)}건")

        draw_no = 1
        new_count = 0
        consecutive_failures = 0

        while consecutive_failures < 3:
            if draw_no in existing:
                draw_no += 1
                consecutive_failures = 0
                continue

            data = fetch_single_draw(draw_no)
            if data is None:
                consecutive_failures += 1
                draw_no += 1
                continue

            consecutive_failures = 0
            collection.update_one(
                {"drwNo": data["drwNo"]},
                {"$set": data},
                upsert=True,
            )
            new_count += 1
            draw_no += 1

            # API rate limiting (0.5초 간격)
            time.sleep(0.5)

        logger.info(f"수집 완료: 신규 {new_count}건, 최종 회차 {draw_no - consecutive_failures - 1}")
        return new_count
    finally:
        client.close()


def collect_latest_draws(**kwargs):
    """최신 회차만 수집한다. 마지막 저장된 회차 이후부터 수집."""
    client = get_mongo_client()
    try:
        db = client[_get_db_name()]
        collection = db["draws"]

        last_doc = collection.find_one(sort=[("drwNo", -1)])
        start_no = (last_doc["drwNo"] + 1) if last_doc else 1

        logger.info(f"최신 데이터 수집 시작: {start_no}회차부터")

        new_count = 0
        draw_no = start_no
        consecutive_failures = 0

        while consecutive_failures < 3:
            data = fetch_single_draw(draw_no)
            if data is None:
                consecutive_failures += 1
                draw_no += 1
                continue

            consecutive_failures = 0
            collection.update_one(
                {"drwNo": data["drwNo"]},
                {"$set": data},
                upsert=True,
            )
            new_count += 1
            draw_no += 1

            time.sleep(0.5)

        logger.info(f"최신 데이터 수집 완료: 신규 {new_count}건")
        return new_count
    finally:
        client.close()


def log_summary(**kwargs):
    """현재 DB 상태를 요약 로그로 출력한다."""
    client = get_mongo_client()
    try:
        db = client[_get_db_name()]
        collection = db["draws"]

        total = collection.count_documents({})
        latest = collection.find_one(sort=[("drwNo", -1)])
        oldest = collection.find_one(sort=[("drwNo", 1)])

        if latest and oldest:
            logger.info(
                f"DB 요약 - 총 {total}건 | "
                f"{oldest['drwNo']}회({oldest['drwNoDate']}) ~ "
                f"{latest['drwNo']}회({latest['drwNoDate']})"
            )
        else:
            logger.info("DB에 데이터 없음")
    finally:
        client.close()


# ─── DAG 1: 초기 전체 데이터 수집 (수동 트리거) ──────────────
with DAG(
    dag_id="lotto_backfill",
    description="로또 전체 회차 데이터 수집 (초기 세팅용)",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["lotto", "backfill"],
) as backfill_dag:

    backfill_task = PythonOperator(
        task_id="collect_all_draws",
        python_callable=collect_all_draws,
    )

    summary_task = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
    )

    backfill_task >> summary_task


# ─── DAG 2: 매주 최신 데이터 수집 ──────────────────────────
with DAG(
    dag_id="lotto_weekly_collect",
    description="매주 일요일 정오(KST) 최신 로또 데이터 수집",
    schedule="0 3 * * 0",  # 매주 일요일 03:00 UTC (= 12:00 KST)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["lotto", "weekly"],
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
) as weekly_dag:

    collect_task = PythonOperator(
        task_id="collect_latest_draws",
        python_callable=collect_latest_draws,
    )

    summary_task_weekly = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
    )

    collect_task >> summary_task_weekly
