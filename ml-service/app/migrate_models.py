"""기존 saved_models/ 파일을 MLflow Registry에 마이그레이션"""

import os
import sys
import pickle

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
sys.path.insert(0, ML_DIR)

import mlflow
import mlflow.pytorch
import mlflow.sklearn
import torch

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
SAVE_DIR = os.path.join(ML_DIR, "saved_models")

PYTORCH_MODELS = {"lstm", "gru", "transformer"}
SKLEARN_MODELS = {"random_forest", "gradient_boosting"}


def migrate():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("lotto-prediction")
    client = mlflow.tracking.MlflowClient()

    for model_type in sorted(PYTORCH_MODELS | SKLEARN_MODELS):
        registry_name = f"lotto-{model_type.replace('_', '-')}"
        try:
            versions = client.get_latest_versions(registry_name)
            if versions:
                print(f"[SKIP] {registry_name} — already registered (v{versions[0].version})")
                continue
        except mlflow.exceptions.MlflowException:
            pass

        if model_type in PYTORCH_MODELS:
            path = os.path.join(SAVE_DIR, f"lotto_{model_type}.pt")
            if not os.path.exists(path):
                print(f"[SKIP] {model_type} — file not found")
                continue

            checkpoint = torch.load(path, map_location="cpu", weights_only=False)
            config = checkpoint.get("model_config", {})
            train_config = checkpoint.get("train_config", {})

            from model.lstm import LottoLSTM
            from model.gru import LottoGRU
            from model.transformer import LottoTransformer

            model_classes = {"lstm": LottoLSTM, "gru": LottoGRU, "transformer": LottoTransformer}
            ModelClass = model_classes[model_type]

            if model_type == "transformer":
                model = ModelClass(
                    d_model=config.get("d_model", 64),
                    nhead=config.get("nhead", 4),
                    num_layers=config.get("num_layers", 2),
                )
            else:
                model = ModelClass(
                    hidden_size=config.get("hidden_size", 128),
                    num_layers=config.get("num_layers", 2),
                )

            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()

            with mlflow.start_run(run_name=f"migrate_{model_type}") as run:
                mlflow.log_params({
                    "model_type": model_type,
                    "seq_length": str(train_config.get("seq_length", 10)),
                    "epochs": str(train_config.get("epochs", 100)),
                    "learning_rate": str(train_config.get("learning_rate", 0.001)),
                    "source": "migration",
                })
                if "best_val_loss" in checkpoint:
                    mlflow.log_metric("best_val_loss", checkpoint["best_val_loss"])

                mlflow.pytorch.log_model(model, artifact_path="model")

                result = mlflow.register_model(f"runs:/{run.info.run_id}/model", registry_name)
                client.transition_model_version_stage(
                    name=registry_name, version=result.version, stage="Production",
                )
                print(f"[OK] {registry_name} v{result.version} → Production")

        else:
            path = os.path.join(SAVE_DIR, f"lotto_{model_type}.pkl")
            if not os.path.exists(path):
                print(f"[SKIP] {model_type} — file not found")
                continue

            with open(path, "rb") as f:
                data = pickle.load(f)

            sk_model = data["model"]
            train_config = data.get("train_config", {})

            with mlflow.start_run(run_name=f"migrate_{model_type}") as run:
                mlflow.log_params({
                    "model_type": model_type,
                    "seq_length": str(train_config.get("seq_length", 10)),
                    "source": "migration",
                })
                if "train_score" in data:
                    mlflow.log_metric("train_score", data["train_score"])

                mlflow.sklearn.log_model(sk_model.model, artifact_path="model")

                result = mlflow.register_model(f"runs:/{run.info.run_id}/model", registry_name)
                client.transition_model_version_stage(
                    name=registry_name, version=result.version, stage="Production",
                )
                print(f"[OK] {registry_name} v{result.version} → Production")


if __name__ == "__main__":
    migrate()
