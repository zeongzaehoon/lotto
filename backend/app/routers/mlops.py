"""MLOps 관련 API - MLflow 실험 조회, 모델 비교"""

import asyncio
import os

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/mlops", tags=["MLOps"])

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")


def _get_mlflow():
    """MLflow 모듈을 가져오고 tracking URI를 설정. 실패 시 None 반환."""
    try:
        import mlflow

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        return mlflow
    except Exception:
        return None


def _list_experiments_sync():
    mlflow = _get_mlflow()
    if not mlflow:
        return None
    experiments = mlflow.search_experiments()
    return [
        {
            "experiment_id": exp.experiment_id,
            "name": exp.name,
            "artifact_location": exp.artifact_location,
            "lifecycle_stage": exp.lifecycle_stage,
        }
        for exp in experiments
    ]


def _list_runs_sync(experiment_name: str, max_results: int):
    mlflow = _get_mlflow()
    if not mlflow:
        return None
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        return {"runs": [], "message": "실험이 아직 없습니다"}

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        max_results=max_results,
        order_by=["start_time DESC"],
    )

    result = []
    for _, row in runs.iterrows():
        run_data = {
            "run_id": row.get("run_id", ""),
            "run_name": row.get("tags.mlflow.runName", ""),
            "status": row.get("status", ""),
            "start_time": str(row.get("start_time", "")),
            "model_type": row.get("params.model_type", ""),
            "epochs": row.get("params.epochs", ""),
            "learning_rate": row.get("params.learning_rate", ""),
            "metrics": {},
        }
        for col in runs.columns:
            if col.startswith("metrics."):
                metric_name = col.replace("metrics.", "")
                val = row[col]
                if val is not None and str(val) != "nan":
                    run_data["metrics"][metric_name] = float(val)

        result.append(run_data)

    return {"runs": result}


def _compare_models_sync():
    mlflow = _get_mlflow()
    if not mlflow:
        return None
    experiment = mlflow.get_experiment_by_name("lotto-prediction")
    if not experiment:
        return {"models": []}

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.best_val_loss ASC"],
    )

    best_by_type = {}
    for _, row in runs.iterrows():
        model_type = row.get("params.model_type", "unknown")
        if model_type not in best_by_type:
            best_by_type[model_type] = {
                "model_type": model_type,
                "run_id": row.get("run_id", ""),
                "best_val_loss": row.get("metrics.best_val_loss"),
                "best_epoch": row.get("metrics.best_epoch"),
                "epochs": row.get("params.epochs", ""),
                "learning_rate": row.get("params.learning_rate", ""),
            }

    return {"models": list(best_by_type.values())}


@router.get("/experiments")
async def list_experiments():
    """MLflow 실험 목록 조회"""
    try:
        result = await asyncio.to_thread(_list_experiments_sync)
        if result is None:
            raise HTTPException(status_code=503, detail="MLflow를 사용할 수 없습니다")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def list_runs(experiment_name: str = "lotto-prediction", max_results: int = 20):
    """MLflow 실행 목록 조회"""
    try:
        result = await asyncio.to_thread(_list_runs_sync, experiment_name, max_results)
        if result is None:
            raise HTTPException(status_code=503, detail="MLflow를 사용할 수 없습니다")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_models():
    """학습된 모델들의 성능 비교"""
    try:
        result = await asyncio.to_thread(_compare_models_sync)
        if result is None:
            raise HTTPException(status_code=503, detail="MLflow를 사용할 수 없습니다")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
