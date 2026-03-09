"""데이터 수집 상태 라우터 - 수집은 Airflow DAG에서 수행"""

import httpx
from fastapi import APIRouter, HTTPException

from app.services import collection_service

router = APIRouter(prefix="/api/collection", tags=["수집"])

AIRFLOW_BASE_URL = "http://airflow-webserver:8080/airflow/api/v1"
AIRFLOW_AUTH = ("admin", "admin")


@router.get("/status")
async def get_status():
    """현재 DB에 저장된 데이터 상태를 반환한다."""
    return await collection_service.get_collection_status()


@router.post("/trigger/{dag_id}")
async def trigger_dag(dag_id: str):
    """Airflow DAG을 트리거한다. 이미 실행 중이면 409를 반환한다."""
    allowed_dags = {"lotto_backfill", "lotto_weekly_collect"}
    if dag_id not in allowed_dags:
        raise HTTPException(status_code=400, detail=f"허용되지 않은 DAG: {dag_id}")

    try:
        async with httpx.AsyncClient() as client:
            # 이미 실행 중인지 확인
            check = await client.get(
                f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns",
                params={"state": "running,queued", "limit": 1},
                auth=AIRFLOW_AUTH,
                timeout=10.0,
            )
            check.raise_for_status()
            active_runs = check.json().get("dag_runs", [])
            if active_runs:
                raise HTTPException(status_code=409, detail="이미 실행 중인 DAG이 있습니다.")

            # DAG이 paused 상태일 수 있으므로 unpause
            await client.patch(
                f"{AIRFLOW_BASE_URL}/dags/{dag_id}",
                json={"is_paused": False},
                auth=AIRFLOW_AUTH,
                timeout=10.0,
            )

            resp = await client.post(
                f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns",
                json={"conf": {}},
                auth=AIRFLOW_AUTH,
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Airflow 서버에 연결할 수 없습니다.")


@router.get("/dag-status/{dag_id}")
async def get_dag_status(dag_id: str):
    """Airflow DAG의 최근 실행 상태를 조회한다."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns",
                params={"order_by": "-execution_date", "limit": 1},
                auth=AIRFLOW_AUTH,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            runs = data.get("dag_runs", [])
            if not runs:
                return {"state": None, "message": "실행 기록 없음"}
            latest = runs[0]
            return {
                "state": latest["state"],
                "dag_run_id": latest["dag_run_id"],
                "execution_date": latest["execution_date"],
                "start_date": latest.get("start_date"),
                "end_date": latest.get("end_date"),
            }
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Airflow 서버에 연결할 수 없습니다.")
