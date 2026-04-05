# backend/pipeline.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.crawler.news_fetcher import fetch_cnyes_news
from backend.crawler.stock_fetcher import fetch_stock_history

from groq import Groq
from dotenv import load_dotenv
from transformers import pipeline as hf_pipeline
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np

load_dotenv(dotenv_path="../.env")
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

# ── 1. 情緒分析 ────────────────────────────────────────────────
_sentiment_model = None

def get_sentiment_model():
    global _sentiment_model
    if _sentiment_model is None:
        print("[載入] FinBERT 模型中...")
        _sentiment_model = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None
        )
    return _sentiment_model

def analyze_sentiment(texts: list) -> pd.DataFrame:
    results = []
    for text in texts:
        trans = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": f"Translate to English, return only the translation:\n{text}"
            }],
            temperature=0.1
        )
        english = trans.choices[0].message.content.strip()
        scores = get_sentiment_model()(english[:512])[0]
        score_dict = {s["label"]: s["score"] for s in scores}
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


# ── 2. 特徵工程 ────────────────────────────────────────────────
def build_features(stock_df: pd.DataFrame, sentiment_score: float) -> pd.DataFrame:
    df = stock_df.copy()
    df["return"]     = df["close"].pct_change()
    df["return_2d"]  = df["close"].pct_change(2)
    df["return_5d"]  = df["close"].pct_change(5)
    df["ma5"]        = df["close"].rolling(5).mean()
    df["ma10"]       = df["close"].rolling(10).mean()
    df["ma5_bias"]   = (df["close"] - df["ma5"])  / df["ma5"]
    df["ma10_bias"]  = (df["close"] - df["ma10"]) / df["ma10"]
    df["volatility"] = df["return"].rolling(5).std()
    df["vol_change"] = df["volume"].pct_change()
    df["vol_ma"]     = df["volume"].rolling(5).mean()
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"]        = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))
    df["sentiment"]  = sentiment_score
    df = df.dropna()
    return df


# ── 3. 預測模型 ────────────────────────────────────────────────
def train_and_predict(df: pd.DataFrame, days: int = 5) -> dict:
    df = df.copy()
    df["target"] = df["close"].pct_change().shift(-1)
    df = df.dropna()

    X = df[FEATURE_COLS].values
    y = df["target"].values

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X_scaled, y)

    last_close    = df["close"].iloc[-1]
    last_row      = df[FEATURE_COLS].iloc[-1].copy()
    predictions   = []
    current_price = last_close

    for _ in range(days):
        x            = scaler.transform([last_row.values])
        pred_return  = float(np.clip(model.predict(x)[0], -0.05, 0.05))
        next_price   = current_price * (1 + pred_return)
        predictions.append(round(next_price, 2))
        last_row["return"]    = pred_return
        last_row["return_2d"] = pred_return
        last_row["return_5d"] = pred_return
        current_price = next_price

    pred_dates = pd.bdate_range(
        start=df.index[-1], periods=days + 1
    )[1:]

    return {
        "last_price":         round(last_close, 2),
        "predictions":        predictions,
        "dates":              [str(d.date()) for d in pred_dates],
        "feature_importance": dict(zip(
            FEATURE_COLS,
            [round(v, 4) for v in model.feature_importances_]
        ))
    }


# ── 4. 主 Pipeline ─────────────────────────────────────────────
def run_pipeline(context: dict) -> dict:
    event   = context["event"]
    ticker  = context["ticker"]
    days    = context["days"]
    company = TICKER_NAME.get(ticker, context.get("company", ticker))

    print(f"\n[Pipeline] 開始分析：{event} × {company}（{ticker}）{days}天")

    print("[1/4] 爬取新聞...")
    news_df = fetch_cnyes_news(keyword=event, max_pages=2)
    if news_df.empty:
        titles = [f"{event}對{company}股價造成影響"]
        print("  → 無新聞，使用 fallback")
    else:
        titles = news_df["title"].tolist()[:10]
        print(f"  → 取得 {len(titles)} 則新聞")

    print("[2/4] 情緒分析...")
    sentiment_df  = analyze_sentiment(titles)
    avg_sentiment = round(sentiment_df["sentiment_score"].mean(), 4)
    print(f"  → 平均情緒分數：{avg_sentiment}")

    print("[3/4] 抓取股價資料...")
    stock_df   = fetch_stock_history(ticker, days=120)
    feature_df = build_features(stock_df, avg_sentiment)

    print("[4/4] 預測中...")
    pred_result = train_and_predict(feature_df, days=days)

    print("\n[✓] 分析完成")
    return {
        "event":            event,
        "ticker":           ticker,
        "company":          company,
        "days":             days,
        "avg_sentiment":    avg_sentiment,
        "news_count":       len(titles),
        "last_price":       pred_result["last_price"],
        "predictions":      pred_result["predictions"],
        "pred_dates":       pred_result["dates"],
        "feature_importance": pred_result["feature_importance"],
        "sentiment_detail": sentiment_df[["text", "sentiment_score"]].to_dict("records")
    }