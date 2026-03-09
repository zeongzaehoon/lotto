"""
scikit-learn 기반 로또 번호 예측 모델

- RandomForestModel: 랜덤포레스트로 각 번호 출현 확률 예측
- GradientBoostingModel: GBT로 각 번호 출현 확률 예측

입력: 과거 N회차의 번호 시퀀스 (flatten)
출력: 45개 번호의 출현 확률
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer


class SklearnLottoModel:
    """scikit-learn 기반 모델의 공통 인터페이스"""

    def __init__(self, model_type: str = "random_forest", seq_length: int = 10):
        self.seq_length = seq_length
        self.model_type = model_type
        self.model: OneVsRestClassifier | None = None
        self.mlb = MultiLabelBinarizer(classes=list(range(1, 46)))
        self.mlb.fit([list(range(1, 46))])  # classes 고정 후 fit 완료

    def _create_base_model(self):
        if self.model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
            )
        elif self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def prepare_data(
        self, draws: list[dict]
    ) -> tuple[np.ndarray, np.ndarray]:
        """시퀀스 데이터 생성

        입력: 과거 seq_length 회차의 번호를 flatten (seq_length * 7 차원)
        타겟: 다음 회차 번호의 multi-label (7개 번호)
        """
        all_vectors = []
        all_labels = []

        for draw in draws:
            vec = draw["numbers"] + [draw["bonusNo"]]
            all_vectors.append(vec)
            all_labels.append(draw["numbers"] + [draw["bonusNo"]])

        X, y_labels = [], []
        for i in range(len(all_vectors) - self.seq_length):
            # flatten: (seq_length, 7) → (seq_length * 7,)
            flat = []
            for j in range(self.seq_length):
                flat.extend(all_vectors[i + j])
            X.append(flat)
            y_labels.append(all_labels[i + self.seq_length])

        X = np.array(X, dtype=np.float32)
        y = self.mlb.transform(y_labels)

        return X, y

    def train(self, X: np.ndarray, y: np.ndarray) -> dict:
        """모델 학습"""
        base_model = self._create_base_model()
        self.model = OneVsRestClassifier(base_model)
        self.model.fit(X, y)

        # 학습 정확도 계산
        train_score = self.model.score(X, y)
        return {"score": float(train_score)}

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """확률 예측 (N, 45)"""
        if self.model is None:
            raise RuntimeError("모델이 학습되지 않았습니다.")

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        # predict_proba 미지원 시 decision_function 사용
        decision = self.model.decision_function(X)
        # sigmoid 변환
        return 1.0 / (1.0 + np.exp(-decision))

    def predict(self, X: np.ndarray) -> dict:
        """다음 회차 예측"""
        probs = self.predict_proba(X)
        if probs.ndim == 1:
            probs = probs.reshape(1, -1)

        probs_last = probs[-1]  # 마지막 샘플의 예측
        indices = np.argsort(probs_last)[::-1]

        main_numbers = sorted((indices[:6] + 1).tolist())
        bonus = int(indices[6] + 1)

        confidences = [float(probs_last[n - 1]) for n in main_numbers]
        bonus_confidence = float(probs_last[bonus - 1])

        return {
            "numbers": main_numbers,
            "bonusNo": bonus,
            "confidence": confidences + [bonus_confidence],
        }
