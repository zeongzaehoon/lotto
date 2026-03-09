"""ML 모델 단위 테스트"""

import sys
import os
import pytest
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model.lstm import LottoLSTM
from model.gru import LottoGRU
from model.transformer import LottoTransformer
from model.sklearn_models import SklearnLottoModel


class TestLottoLSTM:
    def test_output_shape(self):
        model = LottoLSTM(input_size=7, hidden_size=64, num_layers=1)
        x = torch.randn(4, 10, 7)  # batch=4, seq=10, features=7
        out = model(x)
        assert out.shape == (4, 45)

    def test_output_range(self):
        """출력이 0~1 사이 (Sigmoid)"""
        model = LottoLSTM(hidden_size=32, num_layers=1)
        x = torch.randn(2, 10, 7)
        out = model(x)
        assert (out >= 0).all()
        assert (out <= 1).all()

    def test_different_seq_lengths(self):
        """다양한 시퀀스 길이 처리"""
        model = LottoLSTM(hidden_size=32, num_layers=1)
        for seq_len in [5, 10, 20, 50]:
            x = torch.randn(1, seq_len, 7)
            out = model(x)
            assert out.shape == (1, 45)


class TestLottoGRU:
    def test_output_shape(self):
        model = LottoGRU(input_size=7, hidden_size=64, num_layers=1)
        x = torch.randn(4, 10, 7)
        out = model(x)
        assert out.shape == (4, 45)

    def test_output_range(self):
        model = LottoGRU(hidden_size=32, num_layers=1)
        x = torch.randn(2, 10, 7)
        out = model(x)
        assert (out >= 0).all()
        assert (out <= 1).all()


class TestLottoTransformer:
    def test_output_shape(self):
        model = LottoTransformer(d_model=32, nhead=4, num_layers=1)
        x = torch.randn(4, 10, 7)
        out = model(x)
        assert out.shape == (4, 45)

    def test_output_range(self):
        model = LottoTransformer(d_model=32, nhead=4, num_layers=1)
        x = torch.randn(2, 10, 7)
        out = model(x)
        assert (out >= 0).all()
        assert (out <= 1).all()

    def test_different_seq_lengths(self):
        model = LottoTransformer(d_model=32, nhead=4, num_layers=1)
        for seq_len in [5, 10, 30]:
            x = torch.randn(1, seq_len, 7)
            out = model(x)
            assert out.shape == (1, 45)


class TestSklearnModel:
    def _make_draws(self, n=100):
        draws = []
        for i in range(n):
            nums = sorted(np.random.choice(range(1, 46), 6, replace=False).tolist())
            remaining = list(set(range(1, 46)) - set(nums))
            bonus = int(np.random.choice(remaining))
            draws.append({"numbers": nums, "bonusNo": bonus, "drwNo": i + 1})
        return draws

    def test_random_forest_data_prep(self):
        """데이터 준비"""
        model = SklearnLottoModel(model_type="random_forest", seq_length=5)
        draws = self._make_draws(50)
        X, y = model.prepare_data(draws)
        assert X.shape[0] == 45  # 50 - 5 = 45
        assert X.shape[1] == 5 * 7  # seq_length * 7
        assert y.shape == (45, 45)  # multi-hot over 45 numbers

    def test_random_forest_train_predict(self):
        """RF 학습 및 예측"""
        model = SklearnLottoModel(model_type="random_forest", seq_length=5)
        draws = self._make_draws(50)
        X, y = model.prepare_data(draws)
        result = model.train(X, y)
        assert "score" in result
        assert 0 <= result["score"] <= 1

        pred = model.predict(X[-1:])
        assert len(pred["numbers"]) == 6
        assert 1 <= pred["bonusNo"] <= 45
        assert all(1 <= n <= 45 for n in pred["numbers"])

    def test_gradient_boosting_train_predict(self):
        """GBT 학습 및 예측"""
        model = SklearnLottoModel(model_type="gradient_boosting", seq_length=5)
        draws = self._make_draws(50)
        X, y = model.prepare_data(draws)
        result = model.train(X, y)
        assert "score" in result

        pred = model.predict(X[-1:])
        assert len(pred["numbers"]) == 6
        assert len(pred["confidence"]) == 7

    def test_invalid_model_type(self):
        with pytest.raises(ValueError):
            model = SklearnLottoModel(model_type="invalid")
            model._create_base_model()

    def test_predict_before_train(self):
        model = SklearnLottoModel(model_type="random_forest", seq_length=5)
        X = np.random.randn(1, 35).astype(np.float32)
        with pytest.raises(RuntimeError):
            model.predict(X)


class TestTrainDataPrep:
    """train.py의 데이터 준비 함수 테스트"""

    def test_prepare_torch_dataset(self):
        from train import prepare_torch_dataset

        draws = []
        for i in range(30):
            nums = sorted(np.random.choice(range(1, 46), 6, replace=False).tolist())
            remaining = list(set(range(1, 46)) - set(nums))
            bonus = int(np.random.choice(remaining))
            draws.append({"numbers": nums, "bonusNo": bonus, "drwNo": i + 1})

        X, y = prepare_torch_dataset(draws, seq_length=10)
        assert X.shape == (20, 10, 7)  # 30 - 10 = 20 samples
        assert y.shape == (20, 45)
        # 입력값이 0~1 범위
        assert (X >= 0).all()
        assert (X <= 1).all()
        # 타겟이 binary
        assert set(y.unique().tolist()).issubset({0.0, 1.0})

    def test_prepare_torch_dataset_target_correctness(self):
        """타겟 multi-hot이 올바른지 검증"""
        from train import prepare_torch_dataset

        draws = [
            {"numbers": [1, 2, 3, 4, 5, 6], "bonusNo": 7, "drwNo": i}
            for i in range(1, 12)
        ]
        # 마지막 draw의 번호가 타겟
        draws[-1] = {"numbers": [10, 20, 30, 35, 40, 45], "bonusNo": 15, "drwNo": 11}

        X, y = prepare_torch_dataset(draws, seq_length=10)
        assert X.shape == (1, 10, 7)
        # 타겟 검증: 10,15,20,30,35,40,45 → index 9,14,19,29,34,39,44
        target = y[0]
        for num in [10, 15, 20, 30, 35, 40, 45]:
            assert target[num - 1] == 1.0
        # 다른 번호는 0
        assert target[0] == 0.0  # 번호 1
