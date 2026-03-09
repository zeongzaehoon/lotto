#!/bin/bash
set -e

# MLflow DB가 없으면 생성
PGPASSWORD="${POSTGRES_PASSWORD:-airflow}" psql -h postgres -U "${POSTGRES_USER:-airflow}" -tc \
  "SELECT 1 FROM pg_database WHERE datname = 'mlflow'" | grep -q 1 || \
PGPASSWORD="${POSTGRES_PASSWORD:-airflow}" psql -h postgres -U "${POSTGRES_USER:-airflow}" -c \
  "CREATE DATABASE mlflow"

exec mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri "${MLFLOW_BACKEND_STORE_URI}" \
  --default-artifact-root "${MLFLOW_DEFAULT_ARTIFACT_ROOT}" \
  --static-prefix /mlflow
