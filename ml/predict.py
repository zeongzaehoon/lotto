"""
학습된 모델로 로또 번호 예측 (멀티 모델 지원)

[ 추론(Inference)이란? ]
학습이 끝난 모델에 새로운 데이터를 넣어 결과를 얻는 과정.
학습(Training)은 "가중치를 조정하는 것"이고,
추론(Inference)은 "조정된 가중치를 사용해 예측하는 것"이다.

학습 vs 추론 비교:
  학습:  데이터 → 모델 → 예측 → 정답과 비교 → 역전파 → 가중치 업데이트
  추론:  데이터 → 모델 → 예측 (여기서 끝!)

추론 시에는 그래디언트 계산이 필요 없으므로,
torch.no_grad()로 감싸서 메모리를 절약하고 속도를 높인다.

[ 이 파일의 전체 흐름 ]
1. 저장된 모델 파일(.pt 또는 .pkl)을 로드
2. MongoDB에서 최신 N회차 데이터를 가져옴
3. 데이터를 모델 입력 형태로 변환
4. 모델에 넣어 45개 번호의 확률을 얻음
5. 확률이 높은 상위 7개를 선택 (6개 본번호 + 1개 보너스)
"""

import os
import sys
import pickle

import numpy as np
import torch
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model.lstm import LottoLSTM
from model.gru import LottoGRU
from model.transformer import LottoTransformer
from model.sklearn_models import SklearnLottoModel

MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://admin:changeme@localhost:27017/lotto_db?authSource=admin",
)
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "lotto_db")
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")

# ──────────────────────────────────────────────────
# 모델 클래스 매핑 딕셔너리
# 모델 타입 문자열("lstm", "gru", "transformer")로 클래스를 찾을 수 있게 함.
# 새 PyTorch 모델을 추가하면 여기에 등록하면 된다.
# ──────────────────────────────────────────────────
TORCH_MODEL_CLASSES = {
    "lstm": LottoLSTM,
    "gru": LottoGRU,
    "transformer": LottoTransformer,
}

SKLEARN_MODELS = {"random_forest", "gradient_boosting"}
ALL_MODELS = set(TORCH_MODEL_CLASSES.keys()) | SKLEARN_MODELS


def get_model_path(model_type: str) -> str:
    """
    모델 파일 경로 반환

    PyTorch 모델은 .pt, scikit-learn 모델은 .pkl 확장자를 사용한다.
    - .pt (PyTorch): state_dict(가중치)를 torch.save()로 저장한 파일
    - .pkl (pickle): Python 객체를 직렬화한 파일 (scikit-learn 모델)
    """
    if model_type in TORCH_MODEL_CLASSES:
        return os.path.join(SAVE_DIR, f"lotto_{model_type}.pt")
    else:
        return os.path.join(SAVE_DIR, f"lotto_{model_type}.pkl")


def load_torch_model(model_path: str) -> tuple[torch.nn.Module, dict]:
    """
    저장된 PyTorch 모델을 로드하는 함수

    [ 모델 저장/로드의 원리 ]
    PyTorch 모델 저장 시 train.py에서 이런 형태로 저장했다:
        torch.save({
            "model_state_dict": model.state_dict(),  # 가중치
            "model_type": "lstm",                     # 모델 종류
            "model_config": {"hidden_size": 128, ...}, # 하이퍼파라미터
            "train_config": {"seq_length": 10, ...},   # 학습 설정
        }, path)

    로드할 때는 이 과정의 역순을 따른다:
    1. torch.load()로 저장된 딕셔너리를 불러옴
    2. 같은 구조의 빈 모델을 생성 (하이퍼파라미터가 같아야 함!)
    3. load_state_dict()로 저장된 가중치를 빈 모델에 넣음
    4. model.eval()로 추론 모드 전환

    [ map_location 파라미터 ]
    map_location="cpu": GPU로 학습한 모델도 CPU에서 로드할 수 있게 한다.
    만약 학습은 GPU(cuda:0)로 했는데 추론 서버에 GPU가 없으면?
    → map_location 없이 로드하면 에러 발생!
    → "cpu"로 지정하면 GPU 텐서를 CPU로 자동 변환해서 로드한다.

    [ weights_only 파라미터 ]
    weights_only=False: pickle 역직렬화를 허용한다.
    PyTorch 2.0+부터 보안을 위해 기본값이 True로 바뀌었는데,
    우리는 model_config 등 일반 dict도 함께 저장했으므로 False가 필요하다.
    (외부에서 받은 신뢰할 수 없는 모델 파일은 True로 로드하는 것이 안전)
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"모델 파일 없음: {model_path}")

    # Step 1: 저장된 체크포인트(딕셔너리) 로드
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    model_type = checkpoint["model_type"]
    config = checkpoint["model_config"]

    # ──────────────────────────────────────────────────
    # Step 2: 동일한 구조의 빈 모델 인스턴스 생성
    #
    # 왜 빈 모델을 먼저 만들어야 할까?
    # state_dict는 "가중치 값"만 담고 있고, "모델 구조"는 담고 있지 않다.
    # 그래서 모델 구조(어떤 레이어가 어떤 크기로 있는지)를 먼저 정의하고,
    # 그 위에 저장된 가중치를 얹는 방식이다.
    #
    # 비유: 옷걸이(모델 구조)를 먼저 준비하고, 옷(가중치)를 건다.
    #       옷걸이 크기가 다르면 옷이 안 맞듯이,
    #       hidden_size 등이 저장 시와 달라도 에러가 난다.
    # ──────────────────────────────────────────────────
    ModelClass = TORCH_MODEL_CLASSES[model_type]
    if model_type == "transformer":
        model = ModelClass(
            input_size=config.get("input_size", 7),
            d_model=config["d_model"],
            nhead=config["nhead"],
            num_layers=config["num_layers"],
            output_size=config.get("output_size", 45),
            dropout=config.get("dropout", 0.3),
        )
    else:
        # LSTM, GRU는 같은 파라미터 구조
        model = ModelClass(
            input_size=config.get("input_size", 7),
            hidden_size=config["hidden_size"],
            num_layers=config["num_layers"],
            output_size=config.get("output_size", 45),
            dropout=config.get("dropout", 0.3),
        )

    # ──────────────────────────────────────────────────
    # Step 3: 저장된 가중치를 모델에 로드
    #
    # load_state_dict(): state_dict(OrderedDict)의 가중치를
    # 모델의 각 레이어에 매핑하여 덮어씌운다.
    # 키 이름이 일치해야 하므로, 저장 시의 모델 구조와 동일해야 한다.
    # ──────────────────────────────────────────────────
    model.load_state_dict(checkpoint["model_state_dict"])

    # ──────────────────────────────────────────────────
    # Step 4: 추론(evaluation) 모드로 전환
    #
    # model.eval()이 하는 일:
    # 1) Dropout 비활성화: 학습 중에는 30% 뉴런을 끄지만, 추론 시에는 모두 사용
    # 2) BatchNorm 고정: 학습 중 통계를 업데이트하지 않고 저장된 값 사용
    #
    # 이걸 빼먹으면? Dropout이 여전히 동작해서
    # 같은 입력에 대해 매번 다른 결과가 나올 수 있다!
    # ──────────────────────────────────────────────────
    model.eval()
    return model, checkpoint


def load_sklearn_model(model_path: str) -> tuple[SklearnLottoModel, dict]:
    """
    저장된 scikit-learn 모델을 로드하는 함수

    scikit-learn 모델은 Python의 pickle 모듈로 직렬화/역직렬화한다.
    pickle.dump()로 저장하고 pickle.load()로 로드.

    PyTorch와의 차이:
    - PyTorch: 가중치(state_dict)만 저장 → 모델 구조를 코드로 재생성 후 가중치 로드
    - scikit-learn: 모델 객체 전체를 pickle로 저장 → 그대로 로드하면 바로 사용 가능
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"모델 파일 없음: {model_path}")

    with open(model_path, "rb") as f:
        data = pickle.load(f)
    return data["model"], data


def get_latest_draws(seq_length: int) -> list[dict]:
    """
    MongoDB에서 최신 N회차 데이터를 가져오는 함수

    seq_length=10이면 최신 10회차의 당첨번호를 가져온다.
    예측 시 입력으로 사용되며, 학습 시 사용한 seq_length와 동일해야 한다.

    .sort("drwNo", -1): 회차 번호 내림차순 (최신이 먼저)
    .limit(seq_length): seq_length건만 가져오기
    draws.reverse(): 시간순으로 정렬 (오래된 것 → 최신 순서로)
    """
    client = MongoClient(MONGODB_URL)
    try:
        db = client[MONGO_DB_NAME]
        draws = list(
            db.draws.find({}, {"numbers": 1, "bonusNo": 1, "_id": 0})
            .sort("drwNo", -1)
            .limit(seq_length)
        )

        if len(draws) < seq_length:
            raise ValueError(f"데이터 부족: {seq_length}건 필요, {len(draws)}건 존재")

        draws.reverse()  # 시간순 정렬 (과거 → 현재)
        return draws
    finally:
        client.close()


def predict_torch(model_type: str) -> dict:
    """
    PyTorch 모델로 다음 회차 로또 번호를 예측하는 함수

    [ 전체 흐름 ]
    1. 저장된 모델 로드 (load_torch_model)
    2. 최신 N회차 데이터 가져오기 (get_latest_draws)
    3. 데이터를 텐서로 변환
    4. 모델에 넣어 예측 (torch.no_grad)
    5. 확률 → 번호 변환

    [ 데이터 변환 과정 ]
    MongoDB 데이터:
      [{"numbers": [3,11,15,29,35,44], "bonusNo": 7}, ...]

    → 정규화된 벡터 리스트:
      [[3/45, 11/45, 15/45, 29/45, 35/45, 44/45, 7/45], ...]

    → PyTorch 텐서: (1, seq_length, 7)
      unsqueeze(0)으로 배치 차원 추가 (모델은 배치 입력을 기대)
    """
    # Step 1: 모델 로드
    model_path = get_model_path(model_type)
    model, checkpoint = load_torch_model(model_path)
    seq_length = checkpoint["train_config"]["seq_length"]

    # Step 2: 최신 데이터 로드
    draws = get_latest_draws(seq_length)

    # Step 3: 데이터를 정규화된 벡터로 변환
    # 각 번호를 45로 나눠 0~1 범위로 정규화 (학습 시와 동일한 전처리)
    vectors = []
    for draw in draws:
        vec = draw["numbers"] + [draw["bonusNo"]]  # [3,11,15,29,35,44,7]
        vectors.append([v / 45.0 for v in vec])     # [0.067, 0.244, ...]

    # ──────────────────────────────────────────────────
    # Step 4: NumPy 배열 → PyTorch 텐서 변환
    #
    # torch.FloatTensor(): NumPy 배열이나 리스트를 32비트 부동소수점 텐서로 변환
    # .unsqueeze(0): 맨 앞에 차원 추가 → 배치 차원
    #
    # shape 변화:
    #   vectors:  (10, 7) - 10회차, 각 7개 숫자
    #   텐서:     (10, 7) - 아직 배치 없음
    #   unsqueeze: (1, 10, 7) - 배치 1개 추가
    #
    # 왜 배치 차원이 필요한가?
    # 모델은 학습 시 여러 샘플을 한 번에 처리하도록 설계되었다.
    # 추론 시 1개만 넣더라도, (batch, seq_len, features) 형태를 맞춰야 한다.
    # ──────────────────────────────────────────────────
    x = torch.FloatTensor(np.array(vectors)).unsqueeze(0)  # (1, seq_length, 7)

    # ──────────────────────────────────────────────────
    # Step 5: 추론 실행
    #
    # torch.no_grad(): 그래디언트 계산을 비활성화하는 컨텍스트 매니저
    #
    # 왜 필요한가?
    # 기본적으로 PyTorch는 모든 연산의 그래디언트를 추적한다.
    # (역전파로 가중치를 업데이트하기 위해)
    # 하지만 추론에서는 역전파가 필요 없으므로,
    # no_grad()로 추적을 끄면:
    #   - 메모리 사용량 감소 (중간 계산값을 저장 안 함)
    #   - 연산 속도 향상
    #
    # model(x)와 model.forward(x)의 차이:
    # model(x)를 쓰면 PyTorch가 forward() 외에도
    # hook 등의 추가 작업을 자동 처리한다.
    # 항상 model(x)로 호출하는 것이 권장된다.
    #
    # .squeeze(0): 배치 차원 제거 (1, 45) → (45,)
    # .numpy(): PyTorch 텐서를 NumPy 배열로 변환
    #   (no_grad 블록 안이고 CPU 텐서이므로 변환 가능)
    # ──────────────────────────────────────────────────
    with torch.no_grad():
        probs = model(x).squeeze(0).numpy()  # (45,) 각 번호의 출현 확률

    # ──────────────────────────────────────────────────
    # Step 6: 확률 → 로또 번호 변환
    #
    # probs는 45차원 배열로, 각 인덱스가 번호를 나타냄:
    #   probs[0] = 1번 번호의 확률
    #   probs[1] = 2번 번호의 확률
    #   ...
    #   probs[44] = 45번 번호의 확률
    #
    # np.argsort(probs)[::-1]: 확률 높은 순서대로 인덱스 정렬
    #   예) probs = [0.1, 0.9, 0.5] → argsort = [0, 2, 1]
    #       [::-1] 뒤집기 → [1, 2, 0] (0.9가 있는 인덱스1이 첫번째)
    #
    # indices[:6] + 1: 상위 6개 인덱스 → 번호 (0-based → 1-based)
    # indices[6] + 1: 7번째 → 보너스 번호
    # sorted(): 본번호는 오름차순 정렬 (로또 관례)
    # ──────────────────────────────────────────────────
    indices = np.argsort(probs)[::-1]            # 확률 높은 순서
    main_numbers = sorted((indices[:6] + 1).tolist())  # 상위 6개 → 본번호
    bonus = int(indices[6] + 1)                  # 7번째 → 보너스
    confidences = [float(probs[n - 1]) for n in main_numbers]
    bonus_confidence = float(probs[bonus - 1])

    return {
        "numbers": main_numbers,
        "bonusNo": bonus,
        "confidence": confidences + [bonus_confidence],
        "model_version": checkpoint["version"],
        "model_type": model_type,
    }


def predict_sklearn(model_type: str) -> dict:
    """
    scikit-learn 모델로 다음 회차 로또 번호를 예측하는 함수

    PyTorch 모델과의 차이점:
    1. 데이터 형태: 3D 텐서 (batch, seq, 7) 대신 2D 배열 (1, seq*7)로 flatten
    2. 정규화 없음: sklearn은 트리 기반 모델이라 정규화가 필수가 아님
    3. torch.no_grad() 불필요: PyTorch 엔진을 사용하지 않으므로
    4. 로드 방식: pickle.load()로 바로 객체 복원

    데이터 변환:
      10회차 × 7개 번호 = 70차원 벡터 1개로 flatten
      [[3,11,15,29,35,44,7], [1,5,13,...], ...] → [3,11,15,29,35,44,7,1,5,13,...]
    """
    model_path = get_model_path(model_type)
    sk_model, data = load_sklearn_model(model_path)
    seq_length = data["train_config"]["seq_length"]

    draws = get_latest_draws(seq_length)

    # 시퀀스를 1차원으로 flatten (sklearn은 2D 입력을 받음)
    flat = []
    for draw in draws:
        flat.extend(draw["numbers"] + [draw["bonusNo"]])
    X = np.array([flat], dtype=np.float32)  # (1, seq_length * 7)

    result = sk_model.predict(X)
    result["model_version"] = data["version"]
    result["model_type"] = model_type
    return result


def predict(model_type: str = "lstm") -> dict:
    """
    통합 예측 엔트리포인트

    모델 타입에 따라 적절한 예측 함수를 호출한다.
    PyTorch 모델이면 predict_torch(), sklearn 모델이면 predict_sklearn()
    """
    if model_type not in ALL_MODELS:
        raise ValueError(f"지원하지 않는 모델: {model_type}. 사용 가능: {sorted(ALL_MODELS)}")
    if model_type in TORCH_MODEL_CLASSES:
        return predict_torch(model_type)
    else:
        return predict_sklearn(model_type)


def get_available_models() -> list[str]:
    """
    학습 완료된 모델 목록을 반환

    saved_models/ 디렉토리에 모델 파일이 존재하는지 확인한다.
    모델 파일이 있다 = 학습이 완료되어 추론에 사용 가능하다는 의미.
    """
    available = []
    for mt in TORCH_MODEL_CLASSES:
        if os.path.exists(get_model_path(mt)):
            available.append(mt)
    for mt in ["random_forest", "gradient_boosting"]:
        if os.path.exists(get_model_path(mt)):
            available.append(mt)
    return available


# ──────────────────────────────────────────────────
# CLI에서 직접 실행할 때 사용
# 사용법: python predict.py --model lstm
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="lstm")
    args = parser.parse_args()

    result = predict(args.model)
    print(f"[{result['model_type']}] 예측 번호: {result['numbers']}")
    print(f"보너스: {result['bonusNo']}")
    print(f"신뢰도: {[f'{c:.4f}' for c in result['confidence']]}")
