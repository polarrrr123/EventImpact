# backend/model/lstm_model.py
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    "return", "return_2d", "return_5d",
    "ma5_bias", "ma10_bias",
    "volatility", "vol_change",
    "rsi", "sentiment"
]
SEQ_LEN = 20  # 用過去20天預測


# ── LSTM 模型定義 ─────────────────────────────────────────────
class LSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size  = input_size,
            hidden_size = hidden_size,
            num_layers  = num_layers,
            dropout     = dropout,
            batch_first = True
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])  # 取最後一個時間步
        return out.squeeze(-1)


# ── 建立時間序列資料集 ─────────────────────────────────────────
def create_sequences(X: np.ndarray, y: np.ndarray, seq_len: int):
    Xs, ys = [], []
    for i in range(len(X) - seq_len):
        Xs.append(X[i:i + seq_len])
        ys.append(y[i + seq_len])
    return np.array(Xs), np.array(ys)


# ── 訓練並預測 ────────────────────────────────────────────────
def train_and_predict_lstm(df: pd.DataFrame, days: int = 5) -> dict:
    df = df.copy()
    df["target"] = df["close"].pct_change().shift(-1)
    df = df.dropna()

    X_raw = df[FEATURE_COLS].values.astype(np.float32)
    y_raw = df["target"].values.astype(np.float32)

    # 標準化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw).astype(np.float32)

    # 建立序列
    X_seq, y_seq = create_sequences(X_scaled, y_raw, SEQ_LEN)

    # 訓練/測試切分（不 shuffle，時序資料）
    split    = int(len(X_seq) * 0.8)
    X_train  = torch.tensor(X_seq[:split])
    y_train  = torch.tensor(y_seq[:split])

    # 建立模型
    model     = LSTMPredictor(input_size=len(FEATURE_COLS))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    # 訓練
    model.train()
    for epoch in range(80):
        optimizer.zero_grad()
        pred = model(X_train)
        loss = criterion(pred, y_train)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

    # 滾動預測未來 N 天
    model.eval()
    with torch.no_grad():
        last_seq      = X_scaled[-SEQ_LEN:].copy()
        predictions   = []
        current_price = df["close"].iloc[-1]

        for _ in range(days):
            x_tensor    = torch.tensor(last_seq[np.newaxis, :, :])
            pred_return = model(x_tensor).item()
            pred_return = np.clip(pred_return, -0.05, 0.05)
            next_price  = current_price * (1 + pred_return)
            predictions.append(round(float(next_price), 2))

            # 滾動更新序列
            new_row          = last_seq[-1].copy()
            new_row[0]       = pred_return  # 更新 return
            last_seq         = np.vstack([last_seq[1:], new_row])
            current_price    = next_price

    last_date  = df.index[-1]
    pred_dates = pd.bdate_range(start=last_date, periods=days + 1)[1:]

    return {
        "last_price":  round(float(df["close"].iloc[-1]), 2),
        "predictions": predictions,
        "dates":       [str(d.date()) for d in pred_dates],
        "model_type":  "LSTM",
    }