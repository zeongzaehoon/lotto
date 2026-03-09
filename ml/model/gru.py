"""
GRU 기반 로또 번호 예측 모델

[ GRU란? ]
Gated Recurrent Unit. LSTM의 간소화 버전이다.
LSTM은 게이트가 3개(forget, input, output)인데,
GRU는 2개(reset, update)로 줄여서 파라미터가 적고 학습이 빠르다.
성능은 LSTM과 비슷한 경우가 많아서, 먼저 GRU로 실험해보고
부족하면 LSTM을 쓰는 것이 일반적인 전략이다.

[ LSTM vs GRU 차이점 ]
LSTM: cell state(c_t) + hidden state(h_t) 두 개의 상태를 유지
GRU:  hidden state(h_t) 하나만 유지 → 더 단순, 더 빠름

[ 이 모델의 구조 ]
LSTM 모델과 동일한 입출력 인터페이스를 가짐.
내부 RNN 레이어만 nn.LSTM → nn.GRU로 교체.
FC 네트워크는 한 층 줄여서 더 가볍게 설계.
"""

import torch
import torch.nn as nn


class LottoGRU(nn.Module):
    def __init__(
        self,
        input_size: int = 7,       # LSTM과 동일한 입력 (번호6 + 보너스1)
        hidden_size: int = 128,
        num_layers: int = 2,
        output_size: int = 45,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # ──────────────────────────────────────────────────
        # nn.GRU: LSTM과 사용법이 거의 동일하다.
        # 차이점은 반환값에서 cell state(c_n)가 없다는 것:
        #   LSTM: output, (h_n, c_n) = self.lstm(x)
        #   GRU:  output, h_n       = self.gru(x)
        #
        # 파라미터 수 비교 (같은 hidden_size 기준):
        #   LSTM: 4 * (input_size + hidden_size + 1) * hidden_size
        #   GRU:  3 * (input_size + hidden_size + 1) * hidden_size
        #   → GRU가 약 75% 수준의 파라미터를 가짐
        # ──────────────────────────────────────────────────
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        # LSTM보다 FC 네트워크를 한 층 줄임 (모델을 더 가볍게)
        # hidden_size(128) → 256 → ReLU → Dropout → 45 → Sigmoid
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, output_size),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, 7)
        Returns:
            (batch, 45)
        """
        # GRU 통과 - LSTM과 동일하게 사용하면 됨
        # 차이: 반환값이 (output, h_n)으로 c_n이 없다
        gru_out, _ = self.gru(x)

        # 마지막 시점의 출력만 사용 (LSTM과 동일한 패턴)
        last_hidden = gru_out[:, -1, :]
        return self.fc(last_hidden)
