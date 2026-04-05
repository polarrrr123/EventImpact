# backend/pipeline.py
import sys, os
sys.path.append(os.path.dirname(__file__))

from crawler.news_fetcher import fetch_cnyes_news
from crawler.stock_fetcher import fetch_stock_history
from groq import Groq
from dotenv import load_dotenv
from transformers import pipeline as hf_pipeline
import pandas as pd
import numpy as np

load_dotenv(dotenv_path="../.env")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Ticker → 中文名稱對照（修正 company 亂碼問題）
TICKER_NAME = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "0050.TW": "台灣50",
    "0052.TW": "富邦科技",
    "0055.TW": "元大MSCI金融",
}

# ── 1. 情緒分析 ───────────────────────────────────────────────
print("[載入] FinBERT 模型中，首次需要下載約400MB...")
sentiment_model = hf_pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    top_k=None
)

def analyze_sentiment(texts: list[str]) -> pd.DataFrame:
    """
    輸入新聞標題列表，回傳每則的情緒分數
    """
    results = []
    for text in texts:
        # FinBERT 是英文模型，先用 Groq 翻譯
        trans = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": f"Translate to English, return only the translation:\n{text}"
            }],
            temperature=0.1
        )
        english = trans.choices[0].message.content.strip()

        scores = sentiment_model(english[:512])[0]
        score_dict = {s["label"]: s["score"] for s in scores}

        results.append({
            "text":     text,
            "positive": round(score_dict.get("positive", 0), 4),
            "negative": round(score_dict.get("negative", 0), 4),
            "neutral":  round(score_dict.get("neutral",  0), 4),
            "sentiment_score": round(
                score_dict.get("positive", 0) - score_dict.get("negative", 0), 4
            )
        })

    return pd.DataFrame(results)


# ── 2. 特徵工程 ───────────────────────────────────────────────
def build_features(stock_df: pd.DataFrame, sentiment_score: float) -> pd.DataFrame:
    """
    結合股價技術指標 + 情緒分數，建立特徵矩陣
    """
    df = stock_df.copy()

    # 技術指標
    df["ma5"]    = df["close"].rolling(5).mean()
    df["ma10"]   = df["close"].rolling(10).mean()
    df["return"] = df["close"].pct_change()
    df["vol_ma"] = df["volume"].rolling(5).mean()

    # RSI
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))

    # 情緒分數（同一個值貼到每一行）
    df["sentiment"] = sentiment_score

    df = df.dropna()
    return df


# ── 3. 預測模型 ───────────────────────────────────────────────
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = ["ma5", "ma10", "return", "vol_ma", "rsi", "sentiment"]

def train_and_predict(df: pd.DataFrame, days: int = 5) -> dict:
    """
    訓練 GradientBoosting 模型，預測未來 N 天收盤價
    """
    df = df.copy()
    df["target"] = df["close"].shift(-1)  # 預測下一天收盤價
    df = df.dropna()

    X = df[FEATURE_COLS].values
    y = df["target"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)

    # 用最後一筆資料滾動預測 N 天
    last_row = df[FEATURE_COLS].iloc[-1].copy()
    predictions = []
    current_price = df["close"].iloc[-1]

    for _ in range(days):
        x = scaler.transform([last_row.values])
        pred = model.predict(x)[0]
        predictions.append(round(pred, 2))
        # 更新 return 為預測漲跌
        last_row["return"] = (pred - current_price) / current_price
        current_price = pred

    last_date  = df.index[-1]
    pred_dates = pd.bdate_range(start=last_date, periods=days + 1, freq="B")[1:]

    return {
        "last_price":   round(df["close"].iloc[-1], 2),
        "predictions":  predictions,
        "dates":        [str(d.date()) for d in pred_dates],
        "feature_importance": dict(zip(
            FEATURE_COLS,
            [round(v, 4) for v in model.feature_importances_]
        ))
    }


# ── 4. 主 Pipeline ────────────────────────────────────────────
def run_pipeline(context: dict) -> dict:
    """
    接收對話管理器的 context，執行完整分析，回傳結果
    """
    event   = context["event"]
    ticker  = context["ticker"]
    days    = context["days"]
    company = TICKER_NAME.get(ticker, context.get("company", ticker))

    print(f"\n[Pipeline] 開始分析：{event} × {company}（{ticker}）{days}天")

    # Step 1：爬新聞
    print("[1/4] 爬取新聞...")
    news_df = fetch_cnyes_news(keyword=event, max_pages=2)
    if news_df.empty:
        titles = [f"{event}對{company}股價造成影響"]  # fallback
        print("  → 無新聞，使用 fallback 文字")
    else:
        titles = news_df["title"].tolist()[:10]
        print(f"  → 取得 {len(titles)} 則新聞")

    # Step 2：情緒分析
    print("[2/4] 情緒分析...")
    sentiment_df = analyze_sentiment(titles)
    avg_sentiment = round(sentiment_df["sentiment_score"].mean(), 4)
    print(f"  → 平均情緒分數：{avg_sentiment}")

    # Step 3：抓股價 + 建特徵
    print("[3/4] 抓取股價資料...")
    stock_df = fetch_stock_history(ticker, days=120)
    feature_df = build_features(stock_df, avg_sentiment)

    # Step 4：預測
    print("[4/4] 預測中...")
    pred_result = train_and_predict(feature_df, days=days)

    # 整合結果
    result = {
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
        "sentiment_detail": sentiment_df[["text","sentiment_score"]].to_dict("records")
    }

    print("\n[✓] 分析完成")
    return result


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