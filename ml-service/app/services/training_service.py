"""학습 서비스 — ml/train.py 래핑 + Registry 등록"""

import asyncio
import os
import sys

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml")
sys.path.insert(0, ML_DIR)

from app.services.log_manager import log_manager, LogEntry
from app.services import registry_service


async def train_model(
    model_type: str,
    epochs: int = 100,
    learning_rate: float = 0.001,
    seq_length: int = 10,
    session_id: str | None = None,
) -> dict:
    """모델 학습 → MLflow에 기록 → Registry 등록"""
    from train import train as run_train

    loop = asyncio.get_running_loop()
    run_id = session_id or log_manager.active_run_id

    def log_callback(msg: str):
        if run_id:
            asyncio.run_coroutine_threadsafe(
                log_manager.emit(run_id, LogEntry(source="training", message=msg, task_id=model_type)),
                loop,
            )

    # 학습 실행 (blocking → thread)
    result = await asyncio.to_thread(
        run_train,
        model_type=model_type,
        epochs=epochs,
        learning_rate=learning_rate,
        seq_length=seq_length,
        log_callback=log_callback if run_id else None,
    )

    # MLflow run_id가 있으면 Registry에 등록
    mlflow_run_id = result.get("mlflow_run_id")
    registry_info = None
    if mlflow_run_id:
        try:
            registry_info = await asyncio.to_thread(
                registry_service.register_model, mlflow_run_id, model_type
            )
        except Exception as e:
            if run_id:
                asyncio.run_coroutine_threadsafe(
                    log_manager.emit(run_id, LogEntry(source="training", message=f"Registry 등록 실패: {e}", task_id=model_type)),
                    loop,
                )

    result["registry"] = registry_info
    return result
