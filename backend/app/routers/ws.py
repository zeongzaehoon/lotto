"""WebSocket 로그 스트리밍 — Airflow 로그 폴링 + ML Service 학습 로그 릴레이"""

import asyncio
import json
import os

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])

AIRFLOW_BASE_URL = "http://airflow-webserver:8080/airflow/api/v1"
AIRFLOW_AUTH = ("admin", "admin")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8100")


@router.websocket("/api/ws/logs/{dag_id}/{dag_run_id}")
async def stream_dag_logs(websocket: WebSocket, dag_id: str, dag_run_id: str):
    """DAG 실행 로그 스트리밍 (Airflow 폴링)"""
    await websocket.accept()
    try:
        await _poll_airflow(websocket, dag_id, dag_run_id)
    except WebSocketDisconnect:
        pass


@router.websocket("/api/ws/train/{session_id}")
async def stream_train_logs(websocket: WebSocket, session_id: str):
    """학습 로그 스트리밍 — ML Service WebSocket 릴레이"""
    await websocket.accept()
    try:
        await _relay_ml_ws(websocket, session_id)
    except WebSocketDisconnect:
        pass


async def _relay_ml_ws(websocket: WebSocket, session_id: str):
    """ML Service의 WebSocket에 연결하여 메시지를 릴레이"""
    import websockets
    ml_ws_url = ML_SERVICE_URL.replace("http://", "ws://") + f"/ml/ws/train/{session_id}"

    try:
        async with websockets.connect(ml_ws_url) as ml_ws:
            async for message in ml_ws:
                await websocket.send_text(message)
    except Exception:
        # ML Service WebSocket 연결 실패 시 fallback (빈 스트림)
        while True:
            await asyncio.sleep(1)


async def _poll_airflow(websocket: WebSocket, dag_id: str, dag_run_id: str):
    """Airflow REST API를 폴링하여 DAG/task 상태 + task 로그를 푸시"""
    sent_log_lengths: dict[str, int] = {}

    async with httpx.AsyncClient() as client:
        while True:
            try:
                run_resp = await client.get(
                    f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns/{dag_run_id}",
                    auth=AIRFLOW_AUTH, timeout=10.0,
                )
                dag_state = run_resp.json().get("state", "unknown")
                await websocket.send_json({"type": "dag_state", "state": dag_state})

                tasks_resp = await client.get(
                    f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
                    auth=AIRFLOW_AUTH, timeout=10.0,
                )
                tasks = tasks_resp.json().get("task_instances", [])

                for task in tasks:
                    task_id = task["task_id"]
                    task_state = task.get("state") or "pending"
                    await websocket.send_json({
                        "type": "task_state", "task_id": task_id, "state": task_state,
                    })

                    if task_state in ("running", "success", "failed"):
                        try:
                            log_resp = await client.get(
                                f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns/{dag_run_id}"
                                f"/taskInstances/{task_id}/logs/1",
                                auth=AIRFLOW_AUTH, timeout=10.0,
                                headers={"Accept": "text/plain"},
                            )
                            full_log = log_resp.text
                            prev_len = sent_log_lengths.get(task_id, 0)
                            if len(full_log) > prev_len:
                                sent_log_lengths[task_id] = len(full_log)
                                await websocket.send_json({
                                    "type": "airflow_log",
                                    "task_id": task_id,
                                    "content": full_log[prev_len:],
                                })
                        except Exception:
                            pass

                if dag_state in ("success", "failed"):
                    await websocket.send_json({"type": "done", "state": dag_state})
                    return

            except WebSocketDisconnect:
                return
            except Exception:
                pass

            await asyncio.sleep(3)
