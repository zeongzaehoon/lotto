"""MLflow 실험/실행 조회 — 기존 backend의 mlops.py를 이전"""

import asyncio
import os

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/ml", tags=["MLOps"])

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")


def _get_mlflow():
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        return mlflow
    except Exception:
        return None


def _list_experiments():
    mlflow = _get_mlflow()
    if not mlflow:
        return []
    experiments = mlflow.search_experiments()
    return [
        {
            "experiment_id": e.experiment_id,
            "name": e.name,
            "artifact_location": e.artifact_location,
            "lifecycle_stage": e.lifecycle_stage,
        }
        for e in experiments
    ]


def _list_runs(experiment_name: str, max_results: int):
    mlflow = _get_mlflow()
    if not mlflow:
        return []

    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        return []

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        max_results=max_results,
        order_by=["start_time DESC"],
    )

    result = []
    for _, row in runs.iterrows():
        run_data = {
            "run_id": row["run_id"],
            "run_name": row.get("tags.mlflow.runName", ""),
            "status": row["status"],
            "start_time": row["start_time"].isoformat() if hasattr(row["start_time"], "isoformat") else str(row["start_time"]),
        }
        for col in row.index:
            if col.startswith("params."):
                run_data[col.replace("params.", "")] = row[col]
            elif col.startswith("metrics."):
                val = row[col]
                if val == val:  # NaN check
                    run_data[col.replace("metrics.", "")] = val
        result.append(run_data)
    return result


def _compare_models(experiment_name: str):
    mlflow = _get_mlflow()
    if not mlflow:
        return []

    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        return []

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="metrics.best_val_loss > 0",
        order_by=["metrics.best_val_loss ASC"],
    )

    seen = {}
    for _, row in runs.iterrows():
        mt = row.get("params.model_type", "unknown")
        if mt not in seen:
            seen[mt] = {
                "model_type": mt,
                "run_id": row["run_id"],
                "best_val_loss": row.get("metrics.best_val_loss"),
                "best_epoch": row.get("metrics.best_epoch"),
                "epochs": row.get("params.epochs"),
                "learning_rate": row.get("params.learning_rate"),
            }
    return list(seen.values())


@router.get("/experiments")
async def get_experiments():
    result = await asyncio.to_thread(_list_experiments)
    return {"experiments": result}


@router.get("/runs")
async def get_runs(
    experiment_name: str = Query(default="lotto-prediction"),
    max_results: int = Query(default=20, ge=1, le=100),
):
    result = await asyncio.to_thread(_list_runs, experiment_name, max_results)
    return {"runs": result}


@router.get("/compare")
async def compare_models(
    experiment_name: str = Query(default="lotto-prediction"),
):
    result = await asyncio.to_thread(_compare_models, experiment_name)
    return {"models": result}
