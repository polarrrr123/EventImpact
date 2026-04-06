# backend/pipeline.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.crawler.news_fetcher import fetch_cnyes_news
from backend.crawler.stock_fetcher import fetch_stock_history
from groq import Groq
from dotenv import load_dotenv
from transformers import pipeline as hf_pipeline
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from model.lstm_model import train_and_predict_lstm

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TICKER_NAME = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "0050.TW": "台灣50",
    "0052.TW": "富邦科技",
    "0055.TW": "元大MSCI金融",
}

FEATURE_COLS = [
    "return", "return_2d", "return_5d",
    "ma5_bias", "ma10_bias",
    "volatility", "vol_change",
    "rsi", "sentiment"
]

# ── 載入 FinBERT ──────────────────────────────────────────────
print("[載入] FinBERT 模型中...")
sentiment_model = hf_pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    top_k=None
)


# ── 1. 情緒分析 ───────────────────────────────────────────────
def analyze_sentiment(texts: list) -> pd.DataFrame:
    results = []
    for text in texts:
        try:
            trans = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{
                    "role": "user",
                    "content": f"Translate to English, return only the translation:\n{text}"
                }],
                temperature=0.1
            )
            english = trans.choices[0].message.content.strip()
            scores  = sentiment_model(english[:512])[0]
            score_dict = {s["label"]: s["score"] for s in scores}
        except Exception:
            score_dict = {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

        results.append({
            "text":            text,
            "positive":        round(score_dict.get("positive", 0), 4),
            "negative":        round(score_dict.get("negative", 0), 4),
            "neutral":         round(score_dict.get("neutral",  0), 4),
            "sentiment_score": round(
                score_dict.get("positive", 0) - score_dict.get("negative", 0), 4
            )
        })

    return pd.DataFrame(results)


# ── 2. 特徵工程 ───────────────────────────────────────────────
def build_features(stock_df: pd.DataFrame, sentiment_score: float) -> pd.DataFrame:
    df = stock_df.copy()

    # 報酬率
    df["return"]     = df["close"].pct_change()
    df["return_2d"]  = df["close"].pct_change(2)
    df["return_5d"]  = df["close"].pct_change(5)

    # 移動平均乖離率
    df["ma5"]        = df["close"].rolling(5).mean()
    df["ma10"]       = df["close"].rolling(10).mean()
    df["ma5_bias"]   = (df["close"] - df["ma5"])  / df["ma5"]
    df["ma10_bias"]  = (df["close"] - df["ma10"]) / df["ma10"]

    # 波動率
    df["volatility"] = df["return"].rolling(5).std()

    # 成交量變化率
    df["vol_change"] = df["volume"].pct_change()
    df["vol_ma"]     = df["volume"].rolling(5).mean()

    # RSI
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))

    # 情緒分數
    df["sentiment"] = sentiment_score

    # 清理 inf 和 NaN
    df = df.replace([float('inf'), float('-inf')], float('nan'))
    df = df.dropna()
    return df

# ── 3. 預測模型 ───────────────────────────────────────────────
def train_and_predict(df: pd.DataFrame, days: int = 5) -> dict:
    df = df.copy()

    # 預測明天的報酬率
    df["target"] = df["close"].pct_change().shift(-1)
    df = df.dropna()

    X = df[FEATURE_COLS].values
    y = df["target"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X_scaled, y)

    # 滾動預測 N 天
    last_close    = df["close"].iloc[-1]
    last_row      = df[FEATURE_COLS].iloc[-1].copy()
    predictions   = []
    current_price = last_close

    for _ in range(days):
        x           = scaler.transform([last_row.values])
        pred_return = model.predict(x)[0]
        pred_return = np.clip(pred_return, -0.05, 0.05)
        next_price  = current_price * (1 + pred_return)
        predictions.append(round(float(next_price), 2))

        last_row["return"]    = pred_return
        last_row["return_2d"] = pred_return
        last_row["return_5d"] = pred_return
        current_price         = next_price

    last_date  = df.index[-1]
    pred_dates = pd.bdate_range(start=last_date, periods=days + 1)[1:]

    return {
        "last_price":  round(float(last_close), 2),
        "predictions": predictions,
        "dates":       [str(d.date()) for d in pred_dates],
        "feature_importance": dict(zip(
            FEATURE_COLS,
            [round(float(v), 4) for v in model.feature_importances_]
        ))
    }


# ── 4. 主 Pipeline ────────────────────────────────────────────
def run_pipeline(context: dict) -> dict:
    event   = context["event"]
    ticker  = context["ticker"]
    days    = context["days"]
    company = TICKER_NAME.get(ticker, context.get("company", ticker))

    print(f"\n[Pipeline] 開始分析：{event} × {company}（{ticker}）{days}天")

    # Step 1：爬新聞
    print("[1/4] 爬取新聞...")
    news_df = fetch_cnyes_news(keyword=event, max_pages=2)
    if news_df.empty:
        titles = [f"{event}對{company}股價造成影響"]
        print("  → 無新聞，使用 fallback 文字")
    else:
        titles = news_df["title"].tolist()[:10]
        print(f"  → 取得 {len(titles)} 則新聞")

    # Step 2：情緒分析
    print("[2/4] 情緒分析...")
    sentiment_df  = analyze_sentiment(titles)
    avg_sentiment = round(float(sentiment_df["sentiment_score"].mean()), 4)
    print(f"  → 平均情緒分數：{avg_sentiment}")

    # Step 3：股價 + 特徵
    print("[3/4] 抓取股價資料...")
    stock_df   = fetch_stock_history(ticker, days=365)
    feature_df = build_features(stock_df, avg_sentiment)

    # Step 4：預測
    print("[4/4] 預測中...")
    pred_result = train_and_predict_lstm(feature_df, days=days)

    return {
        "event":          event,
        "ticker":         ticker,
        "company":        company,
        "days":           days,
        "avg_sentiment":  avg_sentiment,
        "news_count":     len(titles),
        "last_price":     pred_result["last_price"],
        "predictions":    pred_result["predictions"],
        "pred_dates":     pred_result["dates"],
        "feature_importance": pred_result["feature_importance"],
        "sentiment_detail":   sentiment_df[
            ["text", "sentiment_score"]
        ].to_dict("records")
    }


# ── 測試 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    test_context = {
        "event":   "美中關稅",
        "ticker":  "2330.TW",
        "company": "台積電",
        "days":    5,
        "intent":  "prediction"
    }

    result = run_pipeline(test_context)
    print("\n===== 分析結果 =====")
    print(json.dumps(result, ensure_ascii=False, indent=2))