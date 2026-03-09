"""
로또 번호 예측 모델 학습 스크립트 (멀티 모델 + MLflow 트래킹)

[ PyTorch 학습 루프의 핵심 흐름 ]

  1. 데이터 준비   → Tensor로 변환, DataLoader로 배치 생성
  2. 모델 생성     → nn.Module 상속 클래스 인스턴스화
  3. 손실함수 정의  → 예측과 정답의 차이를 측정하는 함수
  4. 옵티마이저 정의 → 손실을 줄이는 방향으로 가중치를 업데이트하는 알고리즘
  5. 학습 루프:
     for epoch in range(epochs):
       a) model.train()       → 학습 모드 (Dropout 활성화)
       b) 순전파(forward)      → 예측값 계산
       c) 손실 계산(loss)      → 예측 vs 정답
       d) 역전파(backward)     → 각 가중치가 손실에 얼마나 기여했는지 계산
       e) 가중치 업데이트(step) → 기울기 방향으로 가중치 조정
       f) model.eval()        → 평가 모드 (Dropout 비활성화)
       g) 검증(validation)    → 학습 안 한 데이터로 성능 확인
  6. 모델 저장     → state_dict를 파일로 저장

지원 모델:
- lstm: LSTM (PyTorch)
- gru: GRU (PyTorch)
- transformer: Transformer (PyTorch)
- random_forest: Random Forest (scikit-learn)
- gradient_boosting: Gradient Boosting (scikit-learn)
"""

import os
import sys
import pickle
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn

# ──────────────────────────────────────────────────────────
# DataLoader: 데이터를 미니배치로 나누어주는 유틸리티.
# TensorDataset: 여러 Tensor를 하나의 데이터셋으로 묶는다.
#   예) TensorDataset(X, y) → dataset[i] = (X[i], y[i])
# DataLoader(dataset, batch_size=32) → 32개씩 묶어서 반환
# ──────────────────────────────────────────────────────────
from torch.utils.data import DataLoader, TensorDataset
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model.lstm import LottoLSTM
from model.gru import LottoGRU
from model.transformer import LottoTransformer
from model.sklearn_models import SklearnLottoModel

# MLflow (optional - graceful fallback if not available)
try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://admin:changeme@localhost:27017/lotto_db?authSource=admin",
)
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "lotto_db")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")

MODEL_CLASSES = {
    "lstm": LottoLSTM,
    "gru": LottoGRU,
    "transformer": LottoTransformer,
}

SKLEARN_MODELS = {"random_forest", "gradient_boosting"}
ALL_MODELS = set(MODEL_CLASSES.keys()) | SKLEARN_MODELS


def _setup_mlflow(model_type: str) -> bool:
    """MLflow 실험 설정. 연결 실패 시 False 반환."""
    if not MLFLOW_AVAILABLE:
        return False
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment("lotto-prediction")
        return True
    except Exception as e:
        print(f"[MLflow] 연결 실패 (학습은 계속 진행): {e}")
        return False


def load_data_from_mongo() -> list[dict]:
    """MongoDB에서 로또 데이터 로드"""
    client = MongoClient(MONGODB_URL)
    try:
        db = client[MONGO_DB_NAME]
        draws = list(
            db.draws.find({}, {"numbers": 1, "bonusNo": 1, "drwNo": 1, "_id": 0})
            .sort("drwNo", 1)
        )
        return draws
    finally:
        client.close()


def prepare_torch_dataset(
    draws: list[dict], seq_length: int = 10
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    PyTorch 모델용 시퀀스 데이터셋 생성

    [ 데이터 변환 과정 ]

    1) 원본 데이터 (MongoDB에서 가져온 dict 리스트):
       [{"numbers": [3, 11, 15, 29, 35, 44], "bonusNo": 10}, ...]

    2) 정규화 (0~1 범위로 스케일링):
       [[3/45, 11/45, 15/45, 29/45, 35/45, 44/45, 10/45], ...]
       → 신경망은 0~1 범위의 입력에서 가장 잘 학습한다.

    3) 슬라이딩 윈도우로 시퀀스 생성:
       seq_length=3 예시 (실제는 10):
       X[0] = [1회차, 2회차, 3회차]  →  y[0] = 4회차 번호
       X[1] = [2회차, 3회차, 4회차]  →  y[1] = 5회차 번호
       X[2] = [3회차, 4회차, 5회차]  →  y[2] = 6회차 번호

    4) 타겟(y)은 multi-hot 벡터 (45차원):
       다음 회차 번호가 [3, 15, 22, 29, 35, 44] + 보너스 10이면
       → [0,0,1,0,...,1,0,...,1,...,1,...,1,...,1,...0]
          (3번, 10번, 15번, 22번, 29번, 35번, 44번 위치가 1)
    """
    # Step 1: 모든 회차를 7차원 벡터로 변환 후 정규화
    all_vectors = []
    for draw in draws:
        vec = draw["numbers"] + [draw["bonusNo"]]  # [3, 11, 15, 29, 35, 44, 10]
        all_vectors.append([v / 45.0 for v in vec])  # 0~1 정규화

    # Step 2: 슬라이딩 윈도우로 (입력, 타겟) 쌍 생성
    X, y = [], []
    for i in range(len(all_vectors) - seq_length):
        # 입력: i번째부터 seq_length개의 연속된 회차
        X.append(all_vectors[i : i + seq_length])

        # 타겟: 바로 다음 회차의 번호를 multi-hot으로 인코딩
        target = np.zeros(45)  # 45차원 영벡터
        next_draw = draws[i + seq_length]
        for num in next_draw["numbers"]:
            target[num - 1] = 1.0  # 번호는 1~45, 인덱스는 0~44
        target[next_draw["bonusNo"] - 1] = 1.0
        y.append(target)

    # ──────────────────────────────────────────────────────
    # torch.FloatTensor(): numpy 배열 → PyTorch 텐서로 변환.
    # PyTorch는 자체 텐서 타입을 사용하며, 이 위에서 자동 미분이 동작한다.
    # FloatTensor = 32비트 부동소수점 (딥러닝의 기본 타입)
    # ──────────────────────────────────────────────────────
    return (
        torch.FloatTensor(np.array(X)),  # (샘플 수, seq_length, 7)
        torch.FloatTensor(np.array(y)),  # (샘플 수, 45)
    )


def _train_torch(
    model_type: str,
    draws: list[dict],
    epochs: int,
    learning_rate: float,
    seq_length: int,
    batch_size: int,
    hidden_size: int,
    num_layers: int,
) -> dict:
    """
    PyTorch 모델 학습 (LSTM, GRU, Transformer)

    이 함수 하나에 PyTorch 학습의 모든 핵심 개념이 들어있다.
    """

    # ──────────────────────────────────────────────────────
    # Device 설정:
    # GPU(CUDA)가 있으면 GPU에서 연산, 없으면 CPU에서 연산.
    # GPU는 행렬 연산에 특화되어 있어 학습 속도가 10~100배 빠르다.
    # .to(device)로 텐서/모델을 해당 장치로 이동시킨다.
    # ──────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_mlflow = _setup_mlflow(model_type)

    # ── 데이터 준비 ──────────────────────────────────────
    X, y = prepare_torch_dataset(draws, seq_length)
    print(f"[{model_type}] Device: {device} | 데이터셋: X={X.shape}, y={y.shape}")

    # ──────────────────────────────────────────────────────
    # Train/Validation 분할 (80/20):
    # - Train: 모델이 학습하는 데이터
    # - Validation: 학습에 사용하지 않고 성능만 측정하는 데이터
    #
    # 왜 나누는가?
    # Train 데이터에서만 성능이 좋고 새 데이터에서 나쁘면 "과적합(overfitting)".
    # Validation 성능을 모니터링해서 과적합을 감지한다.
    # ──────────────────────────────────────────────────────
    split = int(len(X) * 0.8)

    # ──────────────────────────────────────────────────────
    # DataLoader:
    # - 데이터를 batch_size(32)개씩 묶어서 반환
    # - shuffle=True: 매 epoch마다 데이터 순서를 섞음 (학습 안정화)
    # - 왜 배치로 나누는가?
    #   전체 데이터를 한번에 넣으면 메모리 부족 + 학습 불안정
    #   1개씩 넣으면 너무 느림 + 기울기가 노이즈가 많음
    #   미니배치(32~128)가 속도와 안정성의 균형점
    # ──────────────────────────────────────────────────────
    train_loader = DataLoader(
        TensorDataset(X[:split], y[:split]), batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(X[split:], y[split:]), batch_size=batch_size
    )

    # ── 모델 생성 ────────────────────────────────────────
    ModelClass = MODEL_CLASSES[model_type]
    if model_type == "transformer":
        model = ModelClass(d_model=64, nhead=4, num_layers=num_layers).to(device)
    else:
        model = ModelClass(hidden_size=hidden_size, num_layers=num_layers).to(device)

    # ──────────────────────────────────────────────────────
    # 손실 함수 (Loss Function):
    # BCELoss = Binary Cross Entropy Loss
    #
    # 우리의 출력은 45개 번호 각각의 "출현 확률" (0~1).
    # 타겟은 multi-hot 벡터 (해당 번호면 1, 아니면 0).
    # → 각 번호를 독립적인 이진 분류 문제로 본다.
    #
    # BCE 공식: -[y*log(p) + (1-y)*log(1-p)]
    # - 정답이 1인데 예측이 1에 가까우면 → loss 작음 (잘 맞춤)
    # - 정답이 1인데 예측이 0에 가까우면 → loss 큼 (틀림)
    # ──────────────────────────────────────────────────────
    criterion = nn.BCELoss()

    # ──────────────────────────────────────────────────────
    # 옵티마이저 (Optimizer):
    # Adam = Adaptive Moment Estimation
    #
    # 역전파로 계산된 기울기(gradient)를 사용해 가중치를 업데이트한다.
    # w_new = w_old - learning_rate * gradient
    #
    # Adam은 SGD의 개선판으로:
    # 1) 기울기의 평균(momentum)을 추적 → 진동 감소
    # 2) 기울기의 분산을 추적 → 파라미터별 적응적 학습률
    # 대부분의 경우 Adam이 무난한 선택이다.
    #
    # learning_rate: 한 번에 얼마나 크게 가중치를 조정할지
    # - 너무 크면: 최적점을 지나침 (발산)
    # - 너무 작으면: 학습이 너무 느림
    # - 보통 0.001(1e-3)에서 시작
    # ──────────────────────────────────────────────────────
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    # ──────────────────────────────────────────────────────
    # 학습률 스케줄러 (LR Scheduler):
    # ReduceLROnPlateau: validation loss가 개선되지 않으면 학습률을 줄인다.
    # - patience=10: 10 epoch 동안 개선 없으면 발동
    # - factor=0.5: 학습률을 절반으로 줄임
    #
    # 학습 초기에는 큰 보폭으로 빠르게 이동하고,
    # 수렴 근처에서는 작은 보폭으로 정밀하게 조정하는 전략.
    # ──────────────────────────────────────────────────────
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, patience=10, factor=0.5
    )

    best_val_loss = float("inf")
    best_epoch = 0
    best_state = None  # 가장 좋은 모델의 가중치를 저장

    # MLflow 실험 추적
    mlflow_run = None
    if use_mlflow:
        try:
            mlflow_run = mlflow.start_run(run_name=f"{model_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}")
            mlflow.log_params({
                "model_type": model_type,
                "epochs": epochs,
                "learning_rate": learning_rate,
                "seq_length": seq_length,
                "batch_size": batch_size,
                "hidden_size": hidden_size,
                "num_layers": num_layers,
                "total_draws": len(draws),
                "train_samples": split,
                "val_samples": len(X) - split,
            })
        except Exception:
            use_mlflow = False

    # ════════════════════════════════════════════════════
    # 학습 루프 (Training Loop) - PyTorch의 핵심
    # ════════════════════════════════════════════════════
    try:
        for epoch in range(1, epochs + 1):

            # ── (a) 학습 모드 ────────────────────────────
            # model.train(): Dropout, BatchNorm 등이 학습용으로 동작
            # (Dropout이 랜덤으로 뉴런을 끄고, BatchNorm이 배치 통계 사용)
            model.train()
            train_loss = 0.0

            for bx, by in train_loader:
                # ── 데이터를 device(CPU/GPU)로 이동 ──────
                bx, by = bx.to(device), by.to(device)

                # ── (b) 기울기 초기화 ────────────────────
                # PyTorch는 기울기를 누적(accumulate)하므로,
                # 매 배치마다 이전 기울기를 0으로 리셋해야 한다.
                # 안 하면 이전 배치의 기울기가 더해져서 학습이 엉망이 된다.
                optimizer.zero_grad()

                # ── (c) 순전파 + 손실 계산 ────────────────
                # model(bx): forward() 메서드가 호출됨
                # criterion(예측, 정답): 손실 계산
                loss = criterion(model(bx), by)

                # ── (d) 역전파 (Backpropagation) ─────────
                # loss.backward(): 손실에 대한 모든 파라미터의 기울기를 계산.
                # "이 가중치를 조금 바꾸면 손실이 얼마나 변하는가?"를 자동 계산.
                # 이것이 PyTorch의 자동 미분(autograd) 핵심 기능이다.
                loss.backward()

                # ── (e) 가중치 업데이트 ──────────────────
                # optimizer.step(): 계산된 기울기를 사용해 가중치를 업데이트.
                # w = w - lr * grad  (실제로는 Adam이 더 복잡한 계산을 함)
                optimizer.step()

                train_loss += loss.item()  # .item(): 텐서 → 파이썬 숫자

            train_loss /= max(len(train_loader), 1)  # 평균 loss

            # ── (f) 평가 모드 ────────────────────────────
            # model.eval(): Dropout 비활성화, BatchNorm이 학습된 통계 사용
            # → 추론(inference) 시에는 항상 동일한 결과를 내야 하므로
            model.eval()
            val_loss = 0.0

            # ── (g) 검증 (Validation) ────────────────────
            # torch.no_grad(): 기울기 계산을 비활성화.
            # 검증 시에는 가중치를 업데이트하지 않으므로 기울기가 불필요.
            # 메모리 절약 + 속도 향상 효과.
            with torch.no_grad():
                for bx, by in val_loader:
                    bx, by = bx.to(device), by.to(device)
                    val_loss += criterion(model(bx), by).item()
            val_loss /= max(len(val_loader), 1)

            # 학습률 스케줄러: val_loss를 기준으로 학습률 조정 판단
            scheduler.step(val_loss)

            # ── Best 모델 추적 ───────────────────────────
            # 가장 validation loss가 낮은 epoch의 가중치를 저장.
            # 이렇게 하면 과적합이 시작되기 전의 최적 모델을 보존할 수 있다.
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_epoch = epoch
                # state_dict(): 모델의 모든 가중치를 딕셔너리로 반환
                # .cpu().clone(): GPU 메모리와 독립적으로 복사
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

            # MLflow 메트릭 로깅
            if use_mlflow:
                try:
                    mlflow.log_metrics({
                        "train_loss": train_loss,
                        "val_loss": val_loss,
                        "lr": optimizer.param_groups[0]["lr"],
                    }, step=epoch)
                except Exception:
                    pass

            if epoch % 10 == 0 or epoch == 1:
                print(
                    f"[{model_type}] Epoch {epoch:3d}/{epochs} | "
                    f"Train: {train_loss:.6f} | Val: {val_loss:.6f} | "
                    f"LR: {optimizer.param_groups[0]['lr']:.6f}"
                )
    finally:
        if mlflow_run:
            try:
                mlflow.log_metrics({"best_val_loss": best_val_loss, "best_epoch": best_epoch})
                if best_state:
                    model.load_state_dict(best_state)
                mlflow.pytorch.log_model(model, artifact_path="model")
                mlflow.end_run()
            except Exception:
                try:
                    mlflow.end_run()
                except Exception:
                    pass

    # ════════════════════════════════════════════════════
    # 모델 저장 (Serialization)
    # ════════════════════════════════════════════════════
    # torch.save(): 파이썬 객체를 파일로 저장 (내부적으로 pickle 사용)
    #
    # 저장하는 것:
    # - model_state_dict: 학습된 가중치 (핵심!)
    # - model_config: 모델 구조 재생성에 필요한 하이퍼파라미터
    # - train_config: 재현을 위한 학습 설정
    #
    # 왜 모델 전체가 아닌 state_dict만 저장하는가?
    # → 모델 클래스 코드가 변경되면 pickle이 깨질 수 있다.
    #   state_dict(가중치만)를 저장하면, 새 코드로 모델을 만든 뒤
    #   가중치만 로드할 수 있어서 더 유연하다.
    # ──────────────────────────────────────────────────────
    os.makedirs(SAVE_DIR, exist_ok=True)
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"lotto_{model_type}.pt"
    model_path = os.path.join(SAVE_DIR, filename)

    model_config = {
        "hidden_size": hidden_size,
        "num_layers": num_layers,
        "input_size": 7,
        "output_size": 45,
        "dropout": 0.3,
    }
    if model_type == "transformer":
        model_config = {
            "d_model": 64,
            "nhead": 4,
            "num_layers": num_layers,
            "input_size": 7,
            "output_size": 45,
            "dropout": 0.3,
        }

    torch.save({
        "model_state_dict": best_state or model.state_dict(),
        "model_type": model_type,
        "model_config": model_config,
        "train_config": {
            "epochs": epochs,
            "learning_rate": learning_rate,
            "seq_length": seq_length,
            "batch_size": batch_size,
        },
        "version": version,
        "best_val_loss": best_val_loss,
        "best_epoch": best_epoch,
        "total_draws": len(draws),
    }, model_path)

    print(f"[{model_type}] 저장: {model_path} | Best Val Loss: {best_val_loss:.6f}")

    return {
        "model_path": model_path,
        "model_type": model_type,
        "version": version,
        "epochs": epochs,
        "final_loss": best_val_loss,
    }


def _train_sklearn(
    model_type: str,
    draws: list[dict],
    seq_length: int,
) -> dict:
    """scikit-learn 모델 학습 (PyTorch와 달리 .fit() 한 줄로 끝남)"""
    use_mlflow = _setup_mlflow(model_type)
    print(f"[{model_type}] 학습 시작...")

    sk_model = SklearnLottoModel(model_type=model_type, seq_length=seq_length)
    X, y = sk_model.prepare_data(draws)
    print(f"[{model_type}] 데이터셋: X={X.shape}, y={y.shape}")

    mlflow_run = None
    if use_mlflow:
        try:
            mlflow_run = mlflow.start_run(
                run_name=f"{model_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
            )
            mlflow.log_params({
                "model_type": model_type,
                "seq_length": seq_length,
                "total_draws": len(draws),
                "samples": len(X),
            })
        except Exception:
            use_mlflow = False

    try:
        result = sk_model.train(X, y)

        if use_mlflow:
            try:
                mlflow.log_metric("train_score", result["score"])
                mlflow.sklearn.log_model(sk_model.model, artifact_path="model")
            except Exception:
                pass
    finally:
        if mlflow_run:
            try:
                mlflow.end_run()
            except Exception:
                pass

    os.makedirs(SAVE_DIR, exist_ok=True)
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"lotto_{model_type}.pkl"
    model_path = os.path.join(SAVE_DIR, filename)

    with open(model_path, "wb") as f:
        pickle.dump({
            "model": sk_model,
            "model_type": model_type,
            "train_config": {"seq_length": seq_length},
            "version": version,
            "train_score": result["score"],
            "total_draws": len(draws),
        }, f)

    print(f"[{model_type}] 저장: {model_path} | Score: {result['score']:.4f}")

    return {
        "model_path": model_path,
        "model_type": model_type,
        "version": version,
        "epochs": 1,
        "final_loss": 1.0 - result["score"],
    }


def train(
    model_type: str = "lstm",
    epochs: int = 100,
    learning_rate: float = 0.001,
    seq_length: int = 10,
    batch_size: int = 32,
    hidden_size: int = 128,
    num_layers: int = 2,
) -> dict:
    """통합 학습 엔트리포인트"""
    if model_type not in ALL_MODELS:
        raise ValueError(f"지원하지 않는 모델: {model_type}. 사용 가능: {ALL_MODELS}")

    draws = load_data_from_mongo()
    min_required = seq_length + 20
    if len(draws) < min_required:
        raise ValueError(
            f"데이터 부족: 최소 {min_required}건 필요, 현재 {len(draws)}건"
        )

    if model_type in SKLEARN_MODELS:
        return _train_sklearn(model_type, draws, seq_length)
    else:
        return _train_torch(
            model_type, draws, epochs, learning_rate,
            seq_length, batch_size, hidden_size, num_layers,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="로또 예측 모델 학습")
    parser.add_argument(
        "--model", type=str, default="lstm",
        choices=sorted(ALL_MODELS),
        help="모델 타입",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--seq-length", type=int, default=10)
    args = parser.parse_args()

    train(
        model_type=args.model,
        epochs=args.epochs,
        learning_rate=args.lr,
        seq_length=args.seq_length,
    )
