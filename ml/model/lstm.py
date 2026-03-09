"""
로또 번호 예측을 위한 LSTM 모델

[ LSTM이란? ]
Long Short-Term Memory. RNN(순환신경망)의 한 종류로,
시퀀스(순서가 있는) 데이터에서 패턴을 학습한다.
일반 RNN은 시퀀스가 길어지면 과거 정보를 잊는 문제(vanishing gradient)가 있는데,
LSTM은 "게이트" 메커니즘으로 이를 해결한다.

[ 이 모델의 구조 ]
입력: 과거 N회차의 당첨번호 시퀀스 (N x 7) - 6개 번호 + 보너스
      예) 최근 10회차 → (10, 7) 텐서
출력: 45개 번호 각각의 출현 확률 (45,)
      상위 6개를 당첨번호, 나머지 중 최고를 보너스로 사용
"""

import torch
import torch.nn as nn


# ──────────────────────────────────────────────────────────
# nn.Module: PyTorch에서 모든 신경망의 부모 클래스.
# 우리가 만드는 모든 모델은 nn.Module을 상속받아야 한다.
# 상속하면 .parameters(), .to(device), .train(), .eval() 등
# PyTorch가 제공하는 기능을 자동으로 사용할 수 있다.
# ──────────────────────────────────────────────────────────
class LottoLSTM(nn.Module):
    def __init__(
        self,
        input_size: int = 7,       # 입력 피처 수 (번호 6개 + 보너스 1개 = 7)
        hidden_size: int = 128,    # LSTM 내부 은닉 상태 크기 (클수록 복잡한 패턴 학습 가능, 대신 느림)
        num_layers: int = 2,       # LSTM을 몇 층 쌓을지 (깊을수록 추상적 패턴 학습)
        output_size: int = 45,     # 출력 크기 (로또 번호 1~45)
        dropout: float = 0.3,      # 드롭아웃 비율 (과적합 방지, 0.3 = 30% 뉴런을 랜덤 비활성화)
    ):
        # ──────────────────────────────────────────────────
        # super().__init__(): 부모 클래스(nn.Module)의 초기화.
        # 이걸 빼먹으면 PyTorch가 모델의 파라미터를 추적하지 못한다.
        # ──────────────────────────────────────────────────
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # ──────────────────────────────────────────────────
        # nn.LSTM: PyTorch가 제공하는 LSTM 레이어
        #
        # - input_size: 각 시점(timestep)에서 입력 벡터의 크기
        # - hidden_size: LSTM이 내부적으로 유지하는 "기억"의 크기
        # - num_layers: LSTM을 몇 층 쌓을지 (stacked LSTM)
        #   1층: 입력 → LSTM → 출력
        #   2층: 입력 → LSTM₁ → LSTM₂ → 출력 (더 깊은 패턴 학습)
        # - batch_first=True: 입력 텐서 shape을 (batch, seq_len, features)로 사용
        #   False면 (seq_len, batch, features)인데, True가 직관적
        # - dropout: 층 사이에 적용되는 드롭아웃 (num_layers > 1일 때만 의미)
        # ──────────────────────────────────────────────────
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        # ──────────────────────────────────────────────────
        # nn.Sequential: 여러 레이어를 순서대로 쌓는 컨테이너.
        # 데이터가 위에서 아래로 차례대로 통과한다.
        #
        # 이 FC(Fully Connected) 네트워크의 흐름:
        # hidden_size(128) → 256 → ReLU → Dropout
        #                   → 128 → ReLU → Dropout
        #                   → 45  → Sigmoid
        #
        # nn.Linear(in, out): 완전연결층. y = Wx + b
        # nn.ReLU(): 활성화 함수. 음수 → 0, 양수 → 그대로.
        #           비선형성을 추가해서 복잡한 패턴을 학습 가능하게 함.
        # nn.Dropout(p): 학습 중 p 확률로 뉴런을 꺼서 과적합 방지.
        # nn.Sigmoid(): 출력을 0~1 사이로 압축. "확률"로 해석 가능.
        # ──────────────────────────────────────────────────
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 256),   # 128 → 256 으로 확장
            nn.ReLU(),                     # 활성화
            nn.Dropout(dropout),           # 과적합 방지
            nn.Linear(256, 128),           # 256 → 128 으로 축소
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, output_size),   # 128 → 45 최종 출력
            nn.Sigmoid(),                  # 0~1 확률로 변환
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        순전파(forward): 입력 데이터가 모델을 통과하는 과정을 정의.
        PyTorch에서 model(x)를 호출하면 자동으로 이 메서드가 실행된다.

        Args:
            x: (batch, seq_len, 7) - 정규화된 로또 번호 시퀀스
               예) batch=32, seq_len=10이면 → (32, 10, 7)
               32개의 샘플이 한번에 들어오고, 각 샘플은 10회차 분량,
               각 회차는 7개 숫자(번호6 + 보너스1)

        Returns:
            (batch, 45) - 각 번호(1~45)의 출현 확률
        """
        # ──────────────────────────────────────────────────
        # LSTM에 시퀀스를 넣으면 두 가지가 반환된다:
        # 1) lstm_out: 모든 시점의 출력 (batch, seq_len, hidden_size)
        # 2) (h_n, c_n): 마지막 은닉 상태와 셀 상태 (여기선 사용 안 함)
        #
        # lstm_out의 모양 예시 (batch=32, seq_len=10, hidden=128):
        # [
        #   [시점1 출력, 시점2 출력, ..., 시점10 출력],  ← 샘플 1
        #   [시점1 출력, 시점2 출력, ..., 시점10 출력],  ← 샘플 2
        #   ...
        # ]
        # ──────────────────────────────────────────────────
        lstm_out, _ = self.lstm(x)

        # ──────────────────────────────────────────────────
        # 마지막 시점의 출력만 사용 (many-to-one 구조)
        # [:, -1, :] → "모든 배치의, 마지막 시퀀스 위치의, 전체 hidden"
        #
        # 왜 마지막만? LSTM은 시퀀스를 순서대로 읽으면서
        # 정보를 축적하므로, 마지막 시점에 전체 시퀀스의 정보가
        # 가장 잘 압축되어 있다.
        # ──────────────────────────────────────────────────
        last_hidden = lstm_out[:, -1, :]  # (batch, hidden_size)

        # FC 네트워크를 통과시켜 45차원 확률 벡터로 변환
        out = self.fc(last_hidden)  # (batch, 45)
        return out
