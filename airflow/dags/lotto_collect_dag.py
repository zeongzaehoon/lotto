"""
로또 번호 데이터 수집 DAG

- 초기 실행 시 1회차부터 전체 데이터를 수집 (backfill)
- 이후 매주 일요일 새벽에 최신 회차 데이터를 추가 수집
"""

import os
import time
import logging
from datetime import datetime, timedelta, timezone

import urllib3
import requests
from requests.adapters import HTTPAdapter
from pymongo import MongoClient
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

LOTTO_API_URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do?srchLtEpsd={draw_no}"

# IPv6 timeout 방지: IPv4 강제
urllib3.util.connection.HAS_IPV6 = False


def _get_http_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=urllib3.Retry(total=3, backoff_factor=1))
    session.mount("https://", adapter)
    return session

def get_mongo_client():
    """MongoDB 클라이언트 생성. MONGODB_URL 환경변수 필수."""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL 환경변수가 설정되지 않았습니다.")
    return MongoClient(mongodb_url)


def _get_db_name() -> str:
    return os.getenv("MONGO_DB_NAME", "lotto_db")


def fetch_single_draw(session: requests.Session, draw_no: int) -> dict | None:
    """동행복권 API에서 특정 회차 데이터를 가져온다."""
    url = LOTTO_API_URL.format(draw_no=draw_no)
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        result = resp.json()

        items = result.get("data", {}).get("list", [])
        if not items:
            return None

        data = items[0]
        # ltRflYmd: "20021207" → "2002-12-07"
        raw_date = data.get("ltRflYmd", "")
        drw_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else raw_date

        return {
            "drwNo": data["ltEpsd"],
            "drwNoDate": drw_date,
            "numbers": sorted([
                data["tm1WnNo"], data["tm2WnNo"], data["tm3WnNo"],
                data["tm4WnNo"], data["tm5WnNo"], data["tm6WnNo"],
            ]),
            "bonusNo": data["bnsWnNo"],
            "totSellamnt": data.get("wholEpsdSumNtslAmt", 0),
            "firstWinamnt": data.get("rnk1WnAmt", 0),
            "firstPrzwnerCo": data.get("rnk1WnNope", 0),
            "firstAccumamnt": data.get("rnk1SumWnAmt", 0),
            "collected_at": datetime.now(timezone.utc),
        }
    except Exception as e:
        logger.error(f"회차 {draw_no} 데이터 수집 실패: {e}")
        return None


def collect_all_draws(**kwargs):
    """전체 회차 데이터를 수집한다. 이미 존재하는 회차는 건너뛴다."""
    client = get_mongo_client()
    session = _get_http_session()
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

        while consecutive_failures < 10:
            if draw_no in existing:
                draw_no += 1
                consecutive_failures = 0
                continue

            data = fetch_single_draw(session, draw_no)
            if data is None:
                consecutive_failures += 1
                logger.warning(f"회차 {draw_no} 실패 ({consecutive_failures}/10), {consecutive_failures * 3}초 대기")
                time.sleep(consecutive_failures * 3)
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

            if new_count % 50 == 0:
                logger.info(f"수집 중: {new_count}건 완료, 현재 {draw_no - 1}회차")

            time.sleep(0.3)

        logger.info(f"수집 완료: 신규 {new_count}건, 최종 회차 {draw_no - consecutive_failures - 1}")
        return new_count
    finally:
        session.close()
        client.close()


def collect_latest_draws(**kwargs):
    """최신 회차만 수집한다. 마지막 저장된 회차 이후부터 수집."""
    client = get_mongo_client()
    session = _get_http_session()
    try:
        db = client[_get_db_name()]
        collection = db["draws"]

        last_doc = collection.find_one(sort=[("drwNo", -1)])
        start_no = (last_doc["drwNo"] + 1) if last_doc else 1

        logger.info(f"최신 데이터 수집 시작: {start_no}회차부터")

        new_count = 0
        draw_no = start_no
        consecutive_failures = 0

        while consecutive_failures < 5:
            data = fetch_single_draw(session, draw_no)
            if data is None:
                consecutive_failures += 1
                time.sleep(consecutive_failures * 2)
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

            time.sleep(0.3)

        logger.info(f"최신 데이터 수집 완료: 신규 {new_count}건")
        return new_count
    finally:
        session.close()
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


BACKEND_URL = "http://backend:8000/api"
TRAIN_MODELS = ["lstm", "gru", "transformer", "random_forest", "gradient_boosting"]


def train_all_models(**kwargs):
    """Backend API를 통해 전체 모델을 학습시킨다. MLflow에 자동 기록."""
    session = _get_http_session()
    results = []

    for model_type in TRAIN_MODELS:
        logger.info(f"모델 학습 시작: {model_type}")
        try:
            resp = session.post(
                f"{BACKEND_URL}/train",
                json={
                    "model_type": model_type,
                    "epochs": 100 if model_type not in ("random_forest", "gradient_boosting") else 1,
                    "learning_rate": 0.001,
                    "sequence_length": 10,
                },
                timeout=600,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"모델 학습 완료: {model_type} | loss={result.get('final_loss', 'N/A')}")
            results.append(result)
        except Exception as e:
            logger.error(f"모델 학습 실패: {model_type} | {e}")

    session.close()
    logger.info(f"전체 모델 학습 완료: {len(results)}/{len(TRAIN_MODELS)}개 성공")
    return results


MODEL_REGISTRY_NAMES = [f"lotto-{m.replace('_', '-')}" for m in TRAIN_MODELS]


def promote_models(**kwargs):
    """최신 Staging 모델을 Production으로 승격"""
    session = _get_http_session()
    promoted = 0

    for model_name in MODEL_REGISTRY_NAMES:
        try:
            resp = session.post(
                f"{BACKEND_URL}/mlops/registry/{model_name}/promote",
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"승격 완료: {model_name} v{result.get('version')} → Production")
            promoted += 1
        except Exception as e:
            logger.warning(f"승격 실패/스킵: {model_name} | {e}")

    session.close()
    logger.info(f"모델 승격 완료: {promoted}/{len(MODEL_REGISTRY_NAMES)}개")
    return promoted


# ─── DAG 1: 초기 전체 데이터 수집 + 모델 학습 + 배포 ──────────
with DAG(
    dag_id="lotto_backfill",
    description="로또 전체 회차 데이터 수집 + 모델 학습 + 배포",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["lotto", "backfill"],
) as backfill_dag:

    backfill_task = PythonOperator(
        task_id="collect_all_draws",
        python_callable=collect_all_draws,
    )

    train_task = PythonOperator(
        task_id="train_all_models",
        python_callable=train_all_models,
        execution_timeout=timedelta(hours=1),
    )

    promote_task = PythonOperator(
        task_id="promote_models",
        python_callable=promote_models,
    )

    summary_task = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
    )

    backfill_task >> train_task >> promote_task >> summary_task


# ─── DAG 2: 매주 최신 데이터 수집 + 모델 갱신 + 배포 ─────────
with DAG(
    dag_id="lotto_weekly_collect",
    description="매주 일요일 정오(KST) 최신 로또 데이터 수집 + 모델 갱신 + 배포",
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

    train_task_weekly = PythonOperator(
        task_id="train_all_models",
        python_callable=train_all_models,
        execution_timeout=timedelta(hours=1),
    )

    promote_task_weekly = PythonOperator(
        task_id="promote_models",
        python_callable=promote_models,
    )

    summary_task_weekly = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
    )

    collect_task >> train_task_weekly >> promote_task_weekly >> summary_task_weekly
