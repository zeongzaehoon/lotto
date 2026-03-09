"""MLflow Model Registry 서비스 — 모델 버전 관리 및 스테이지 전이"""

import os
import mlflow
from mlflow.tracking import MlflowClient

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

PYTORCH_MODELS = {"lstm", "gru", "transformer"}
SKLEARN_MODELS = {"random_forest", "gradient_boosting"}
ALL_MODELS = PYTORCH_MODELS | SKLEARN_MODELS


def _client() -> MlflowClient:
    return MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)


def model_name(model_type: str) -> str:
    """model_type → Registry 이름"""
    return f"lotto-{model_type.replace('_', '-')}"


def register_model(run_id: str, model_type: str) -> dict:
    """학습 완료된 run의 모델을 Registry에 등록하고 Staging으로 전이"""
    client = _client()
    name = model_name(model_type)
    model_uri = f"runs:/{run_id}/model"

    # 등록
    result = mlflow.register_model(model_uri, name)

    # Staging으로 전이
    client.transition_model_version_stage(
        name=name,
        version=result.version,
        stage="Staging",
    )

    # 메타 태그 저장
    run = client.get_run(run_id)
    for key in ("seq_length", "model_type", "epochs", "learning_rate"):
        val = run.data.params.get(key)
        if val:
            client.set_model_version_tag(name, result.version, key, val)

    return {
        "name": name,
        "version": int(result.version),
        "stage": "Staging",
        "run_id": run_id,
    }


def promote_to_production(name: str, version: int) -> dict:
    """특정 버전을 Production으로 승격 (기존 Production은 Archived)"""
    client = _client()

    # 기존 Production 버전 Archive
    for mv in client.get_latest_versions(name, stages=["Production"]):
        client.transition_model_version_stage(
            name=name, version=mv.version, stage="Archived",
        )

    # 새 버전 Production으로
    client.transition_model_version_stage(
        name=name, version=str(version), stage="Production",
    )

    return {"name": name, "version": version, "stage": "Production"}


def transition_stage(name: str, version: int, stage: str) -> dict:
    """모델 버전의 스테이지를 변경"""
    client = _client()
    client.transition_model_version_stage(
        name=name, version=str(version), stage=stage,
    )
    return {"name": name, "version": version, "stage": stage}


def list_versions(name: str) -> list[dict]:
    """특정 모델의 전체 버전 목록"""
    client = _client()
    try:
        versions = client.get_latest_versions(name, stages=["None", "Staging", "Production", "Archived"])
    except mlflow.exceptions.MlflowException:
        return []

    return [
        {
            "version": int(v.version),
            "stage": v.current_stage,
            "run_id": v.run_id,
            "created_at": v.creation_timestamp,
            "description": v.description or "",
            "tags": {t.key: t.value for t in (client.get_model_version(name, v.version).tags or [])},
        }
        for v in versions
    ]


def get_available_models(stage: str = "Production") -> list[dict]:
    """지정 스테이지에 모델이 있는 모델 타입 목록"""
    client = _client()
    result = []
    for mt in ALL_MODELS:
        name = model_name(mt)
        try:
            versions = client.get_latest_versions(name, stages=[stage])
            if versions:
                v = versions[0]
                result.append({
                    "model_type": mt,
                    "name": name,
                    "version": int(v.version),
                    "stage": stage,
                    "run_id": v.run_id,
                })
        except mlflow.exceptions.MlflowException:
            continue
    return result


def load_model(model_type: str, stage: str = "Production"):
    """Registry에서 모델 로드"""
    name = model_name(model_type)

    if model_type in PYTORCH_MODELS:
        import mlflow.pytorch
        return mlflow.pytorch.load_model(f"models:/{name}/{stage}")
    else:
        import mlflow.sklearn
        return mlflow.sklearn.load_model(f"models:/{name}/{stage}")


def get_model_meta(model_type: str, stage: str = "Production") -> dict | None:
    """Registry에서 모델 메타 정보 조회"""
    client = _client()
    name = model_name(model_type)
    try:
        versions = client.get_latest_versions(name, stages=[stage])
        if not versions:
            return None
        v = versions[0]
        run = client.get_run(v.run_id)
        return {
            "version": int(v.version),
            "stage": stage,
            "run_id": v.run_id,
            "params": run.data.params,
            "metrics": run.data.metrics,
        }
    except mlflow.exceptions.MlflowException:
        return None
