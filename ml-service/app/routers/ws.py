"""학습 로그 WebSocket 스트리밍"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.log_manager import log_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ml/ws/train/{session_id}")
async def stream_train_logs(websocket: WebSocket, session_id: str):
    await websocket.accept()
    queue = log_manager.register(session_id)
    log_manager.active_run_id = session_id

    try:
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json({
                    "type": "training_log",
                    "source": entry.source,
                    "message": entry.message,
                    "task_id": entry.task_id,
                })
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        log_manager.unregister(session_id, queue)
        if log_manager.active_run_id == session_id:
            log_manager.active_run_id = None
