# backend/model/evaluator.py
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURE_COLS = [
    "return", "return_2d", "return_5d",
    "ma5_bias", "ma10_bias",
    "volatility", "vol_change",
    "rsi", "sentiment"
]

def evaluate_model(df: pd.DataFrame) -> dict:
    """
    用 TimeSeriesSplit 做交叉驗證，回傳評估指標
    """
    df = df.copy()
    df["target"] = df["close"].shift(-1)
    df = df.dropna()

    X = df[FEATURE_COLS].values
    y = df["target"].values

    tscv = TimeSeriesSplit(n_splits=5)
    maes, rmses, direction_accs = [], [], []

    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test  = scaler.transform(X_test)

        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # 基本指標
        maes.append(mean_absolute_error(y_test, y_pred))
        rmses.append(np.sqrt(mean_squared_error(y_test, y_pred)))

        # 方向準確率（預測漲跌方向對不對）
        actual_close = df["close"].values[test_idx]
        actual_dir   = (y_test    > actual_close).astype(int)
        pred_dir     = (y_pred    > actual_close).astype(int)
        direction_accs.append((actual_dir == pred_dir).mean())

    return {
        "mae":               round(float(np.mean(maes)),           2),
        "rmse":              round(float(np.mean(rmses)),          2),
        "direction_accuracy": round(float(np.mean(direction_accs)), 4),
        "cv_folds":          5,
    }


def backtest(df: pd.DataFrame) -> dict:
    """
    簡單回測：用預測方向決定買賣，計算累積報酬
    """
    df = df.copy()
    df["target"] = df["close"].shift(-1)
    df = df.dropna()

    X = df[FEATURE_COLS].values
    y = df["target"].values

    # 用前 70% 訓練，後 30% 回測
    split = int(len(X) * 0.7)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X[:split])
    X_test  = scaler.transform(X[split:])

    model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y[:split])
    y_pred = model.predict(X_test)

    # 回測邏輯
    close_test  = df["close"].values[split:]
    returns     = []
    signals     = []

    for i in range(len(y_pred) - 1):
        predicted_up = y_pred[i] > close_test[i]
        actual_return = (close_test[i + 1] - close_test[i]) / close_test[i]

        # 預測漲就做多，預測跌就做空
        signal = 1 if predicted_up else -1
        strategy_return = signal * actual_return

        returns.append(strategy_return)
        signals.append(signal)

    returns   = np.array(returns)
    cum_return = float(np.prod(1 + returns) - 1)

    # 買進持有報酬（基準）
    bh_return = float(
        (close_test[-1] - close_test[0]) / close_test[0]
    )

    # 最大回撤
    cum_curve  = np.cumprod(1 + returns)
    peak       = np.maximum.accumulate(cum_curve)
    drawdown   = (cum_curve - peak) / peak
    max_drawdown = float(drawdown.min())

    # 夏普比率（假設無風險利率 0）
    sharpe = float(
        np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)
    )

    # 每日報酬序列（給前端畫圖用）
    dates = df.index[split:split + len(returns)].strftime("%Y-%m-%d").tolist()
    cum_returns_list = (cum_curve - 1).round(4).tolist()

    return {
        "strategy_return":  round(cum_return,   4),
        "buyhold_return":   round(bh_return,    4),
        "max_drawdown":     round(max_drawdown, 4),
        "sharpe_ratio":     round(sharpe,       4),
        "win_rate":         round((returns > 0).mean(), 4),
        "total_trades":     len(returns),
        "backtest_dates":   dates,
        "cum_returns":      cum_returns_list,
    }


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from crawler.stock_fetcher import fetch_stock_history
    from pipeline import build_features
    import json

    print("抓取台積電資料...")
    stock_df   = fetch_stock_history("2330.TW", days=365)
    feature_df = build_features(stock_df, sentiment_score=0.0)

    print("\n=== 模型評估 ===")
    eval_result = evaluate_model(feature_df)
    print(json.dumps(eval_result, indent=2))

    print("\n=== 回測結果 ===")
    bt_result = backtest(feature_df)
    print(json.dumps({k: v for k, v in bt_result.items()
                      if k not in ["backtest_dates", "cum_returns"]}, indent=2))