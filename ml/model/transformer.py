"""
Transformer 기반 로또 번호 예측 모델

[ Transformer란? ]
2017년 "Attention Is All You Need" 논문에서 등장.
RNN 계열(LSTM, GRU)과 달리 순서대로 처리하지 않고,
Self-Attention으로 시퀀스 내 모든 위치를 한번에 비교한다.

장점: 병렬처리 가능, 긴 시퀀스에서도 장기 의존성 포착
단점: 위치 정보가 없어서 Positional Encoding이 필요

[ LSTM/GRU vs Transformer ]
LSTM/GRU: 시점1 → 시점2 → 시점3 → ... (순차 처리)
Transformer: 모든 시점을 동시에 보고 "어디가 중요한지" 학습

[ Self-Attention 직관적 이해 ]
"10회차 전 데이터"와 "2회차 전 데이터" 중
다음 회차 예측에 뭐가 더 중요한지를 모델이 스스로 학습한다.
"""

import math

import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    위치 인코딩 (Positional Encoding)

    Transformer는 입력 순서를 모르기 때문에,
    "이 데이터는 시퀀스의 몇 번째인지" 정보를 직접 주입해야 한다.

    sin/cos 함수로 각 위치마다 고유한 벡터를 생성한다.
    - 위치 0: [sin(0), cos(0), sin(0), cos(0), ...]
    - 위치 1: [sin(1/10000^0), cos(1/10000^0), ...]
    - 위치 2: [sin(2/10000^0), cos(2/10000^0), ...]
    각 위치마다 다른 패턴이 생겨서, 모델이 위치를 구분할 수 있다.
    """

    def __init__(self, d_model: int, max_len: int = 100):
        super().__init__()
        # (max_len, d_model) 크기의 위치 인코딩 테이블을 미리 계산
        pe = torch.zeros(max_len, d_model)

        # position: [[0], [1], [2], ...] 각 위치의 인덱스
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)

        # div_term: 주파수를 결정하는 값. 차원이 높을수록 주파수가 낮아짐
        # 이렇게 하면 가까운 위치끼리는 비슷하고, 먼 위치끼리는 다른 값을 가짐
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )

        # 짝수 차원: sin, 홀수 차원: cos
        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model % 2 == 0:
            pe[:, 1::2] = torch.cos(position * div_term)
        else:
            pe[:, 1::2] = torch.cos(position * div_term[: d_model // 2])

        pe = pe.unsqueeze(0)  # (1, max_len, d_model) - 배치 차원 추가

        # ──────────────────────────────────────────────────
        # register_buffer: 학습되지 않는 텐서를 모델에 등록.
        # model.parameters()에는 포함되지 않지만 (학습 안 됨),
        # model.to(device)하면 같이 이동하고,
        # model.state_dict()에도 포함된다.
        # "위치 인코딩은 고정값이지만 모델의 일부"이므로 buffer로 등록.
        # ──────────────────────────────────────────────────
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 입력 임베딩에 위치 인코딩을 더한다
        # x: (batch, seq_len, d_model) + pe: (1, seq_len, d_model)
        # 브로드캐스팅으로 모든 배치에 같은 위치 정보가 추가됨
        return x + self.pe[:, : x.size(1), :]


class LottoTransformer(nn.Module):
    def __init__(
        self,
        input_size: int = 7,      # 입력 피처 수 (번호6 + 보너스1)
        d_model: int = 64,        # Transformer 내부 차원 (모든 레이어에서 사용하는 벡터 크기)
        nhead: int = 4,           # Multi-Head Attention의 헤드 수 (d_model을 nhead로 나눠 병렬 어텐션)
        num_layers: int = 2,      # Transformer Encoder 블록을 몇 개 쌓을지
        output_size: int = 45,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.d_model = d_model

        # ──────────────────────────────────────────────────
        # input_proj: 입력 차원(7)을 d_model(64)로 투영(projection)
        # Transformer는 내부적으로 d_model 차원을 기준으로 동작하므로,
        # 입력을 먼저 그 크기에 맞춰야 한다.
        # ──────────────────────────────────────────────────
        self.input_proj = nn.Linear(input_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model)

        # ──────────────────────────────────────────────────
        # TransformerEncoderLayer: Transformer의 한 블록.
        # 내부 구조:
        #   1) Multi-Head Self-Attention
        #      → 시퀀스 내 모든 위치끼리 관계를 계산
        #   2) Feed-Forward Network
        #      → 각 위치를 독립적으로 비선형 변환
        #   3) 각 단계마다 Residual Connection + LayerNorm
        #
        # - d_model: 입출력 차원
        # - nhead: 어텐션 헤드 수 (d_model=64, nhead=4 → 각 헤드가 16차원 담당)
        # - dim_feedforward: FFN의 중간 차원 (보통 d_model의 4배)
        # - batch_first=True: 입력 shape이 (batch, seq_len, d_model)
        # ──────────────────────────────────────────────────
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,  # 64 * 4 = 256
            dropout=dropout,
            batch_first=True,
        )

        # 위 블록을 num_layers개 쌓아서 Encoder 완성
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers
        )

        # 최종 분류를 위한 FC 네트워크 (LSTM/GRU와 동일한 패턴)
        self.fc = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, output_size),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, 7)
        Returns:
            (batch, 45)
        """
        # ──────────────────────────────────────────────────
        # Step 1: 입력 투영 + 스케일링
        # 원래 Transformer 논문에서는 임베딩에 sqrt(d_model)을 곱한다.
        # 이유: Positional Encoding과 크기를 맞추기 위해.
        # PE의 값은 -1~1 범위인데, 임베딩 값이 너무 작으면 PE에 묻힌다.
        # ──────────────────────────────────────────────────
        x = self.input_proj(x) * math.sqrt(self.d_model)  # (batch, seq_len, d_model)

        # Step 2: 위치 인코딩 추가
        x = self.pos_encoder(x)  # (batch, seq_len, d_model)

        # Step 3: Transformer Encoder 통과
        # Self-Attention으로 시퀀스 내 모든 위치 간의 관계를 학습
        x = self.transformer_encoder(x)  # (batch, seq_len, d_model)

        # Step 4: 마지막 시퀀스 위치의 출력 사용 (LSTM/GRU와 동일한 전략)
        # 다른 방법: 평균 풀링(x.mean(dim=1))도 가능하지만,
        # 마지막 위치가 가장 최신 정보를 반영하므로 이 방식을 사용
        x = x[:, -1, :]  # (batch, d_model)

        return self.fc(x)  # (batch, 45)
