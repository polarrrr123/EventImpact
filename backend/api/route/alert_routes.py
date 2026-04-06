# backend/api/route/alert_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from database import get_db, Portfolio, Alert, User
from api.auth import get_current_user
from crawler.stock_fetcher import fetch_stock_history
from crawler.news_fetcher import fetch_cnyes_news
from pipeline import build_features, analyze_sentiment
from model.lstm_model import train_and_predict_lstm
import numpy as np

router = APIRouter(prefix="/alerts", tags=["alerts"])


def compute_risk_score(ticker: str, company_name: str) -> dict:
    """
    綜合評分預警：LSTM預測跌幅 + RSI + 均線死叉 + 新聞情緒
    滿分100，>=60 danger，>=35 warning，<35 safe
    """
    score_detail = {}

    # ── 抓股價資料 ────────────────────────────────────────────
    stock_df   = fetch_stock_history(ticker, days=365)
    feature_df = build_features(stock_df, sentiment_score=0.0)

    # ── 1. LSTM 預測跌幅（0-40分）────────────────────────────
    pred        = train_and_predict_lstm(feature_df, days=5)
    last_price  = pred["last_price"]
    predictions = pred["predictions"]
    min_price   = min(predictions)
    pred_return = (min_price - last_price) / last_price

    if pred_return < -0.05:
        lstm_score = 40
    elif pred_return < -0.04:
        lstm_score = 32
    elif pred_return < -0.03:
        lstm_score = 24
    elif pred_return < -0.02:
        lstm_score = 16
    elif pred_return < -0.01:
        lstm_score = 8
    else:
        lstm_score = 0

    score_detail["lstm_pred"] = {
        "score":          lstm_score,
        "max_score":      40,
        "predicted_drop": round(pred_return * 100, 2),
        "desc":           f"預測最大跌幅 {pred_return*100:.1f}%"
    }

    # ── 2. RSI 超買（0-20分）─────────────────────────────────
    rsi = feature_df["rsi"].iloc[-1]
    if rsi > 80:
        rsi_score = 20
    elif rsi > 70:
        rsi_score = 14
    elif rsi > 65:
        rsi_score = 7
    else:
        rsi_score = 0

    score_detail["rsi"] = {
        "score":     rsi_score,
        "max_score": 20,
        "value":     round(float(rsi), 2),
        "desc":      f"RSI {rsi:.1f}（{'超買區間' if rsi > 70 else '正常'}）"
    }

    # ── 3. 均線死叉（0-20分）─────────────────────────────────
    ma5_now  = feature_df["ma5"].iloc[-1]
    ma10_now = feature_df["ma10"].iloc[-1]
    ma5_prev = feature_df["ma5"].iloc[-2]
    ma10_prev= feature_df["ma10"].iloc[-2]

    # 死叉：MA5 從上方穿越 MA10
    is_death_cross = (ma5_prev >= ma10_prev) and (ma5_now < ma10_now)
    # MA5 已在 MA10 下方
    is_below       = ma5_now < ma10_now

    if is_death_cross:
        ma_score = 20
        ma_desc  = "均線死叉（賣出信號）"
    elif is_below:
        ma_score = 10
        ma_desc  = "MA5 在 MA10 下方（偏弱）"
    else:
        ma_score = 0
        ma_desc  = "均線正常（MA5 在 MA10 上方）"

    score_detail["moving_avg"] = {
        "score":     ma_score,
        "max_score": 20,
        "ma5":       round(float(ma5_now), 2),
        "ma10":      round(float(ma10_now), 2),
        "desc":      ma_desc
    }

    # ── 4. 新聞情緒（0-20分）─────────────────────────────────
    try:
        news_df = fetch_cnyes_news(keyword=company_name, max_pages=1)
        if news_df.empty:
            sentiment_score = 0.0
            sentiment_desc  = "無相關新聞"
            news_score      = 0
        else:
            titles     = news_df["title"].tolist()[:5]
            sent_df    = analyze_sentiment(titles)
            avg_sent   = float(sent_df["sentiment_score"].mean())
            sentiment_score = avg_sent

            if avg_sent < -0.3:
                news_score = 20
                sentiment_desc = f"新聞情緒極負面（{avg_sent:.2f}）"
            elif avg_sent < -0.1:
                news_score = 12
                sentiment_desc = f"新聞情緒偏負面（{avg_sent:.2f}）"
            elif avg_sent < 0.1:
                news_score = 4
                sentiment_desc = f"新聞情緒中性（{avg_sent:.2f}）"
            else:
                news_score = 0
                sentiment_desc = f"新聞情緒正面（{avg_sent:.2f}）"
    except Exception:
        news_score      = 0
        sentiment_score = 0.0
        sentiment_desc  = "情緒分析失敗"

    score_detail["sentiment"] = {
        "score":     news_score,
        "max_score": 20,
        "value":     round(sentiment_score, 4),
        "desc":      sentiment_desc
    }

    # ── 綜合評分 ──────────────────────────────────────────────
    total_score = lstm_score + rsi_score + ma_score + news_score

    if total_score >= 60:
        alert_type = "danger"
        message    = f"綜合風險評分 {total_score}/100，建議評估出場"
    elif total_score >= 35:
        alert_type = "warning"
        message    = f"綜合風險評分 {total_score}/100，請密切關注"
    else:
        alert_type = "safe"
        message    = f"綜合風險評分 {total_score}/100，目前風險偏低"

    return {
        "ticker":           ticker,
        "company_name":     company_name,
        "alert_type":       alert_type,
        "total_score":      total_score,
        "predicted_return": round(pred_return, 4),
        "message":          message,
        "last_price":       last_price,
        "predictions":      predictions,
        "pred_dates":       pred["dates"],
        "score_detail":     score_detail,
    }


@router.get("/scan")
def scan_portfolio(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user)
):
    stocks = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    if not stocks:
        return {"alerts": [], "message": "倉庫中沒有持股"}

    results = []
    for stock in stocks:
        try:
            result = compute_risk_score(stock.ticker, stock.company_name)

            # 儲存預警紀錄
            if result["alert_type"] in ["danger", "warning"]:
                alert = Alert(
                    user_id          = user.id,
                    ticker           = stock.ticker,
                    company_name     = stock.company_name,
                    alert_type       = result["alert_type"],
                    predicted_return = result["predicted_return"],
                    message          = result["message"],
                )
                db.add(alert)

            results.append(result)
        except Exception as e:
            results.append({
                "ticker":       stock.ticker,
                "company_name": stock.company_name,
                "alert_type":   "unknown",
                "total_score":  0,
                "message":      f"分析失敗：{str(e)}",
            })

    db.commit()

    order = {"danger": 0, "warning": 1, "safe": 2, "unknown": 3}
    results.sort(key=lambda x: order.get(x["alert_type"], 3))

    return {"alerts": results}


@router.get("/history")
def get_alert_history(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user)
):
    alerts = db.query(Alert)\
               .filter(Alert.user_id == user.id)\
               .order_by(Alert.created_at.desc())\
               .limit(50)\
               .all()
    return [
        {
            "id":               a.id,
            "ticker":           a.ticker,
            "company_name":     a.company_name,
            "alert_type":       a.alert_type,
            "predicted_return": a.predicted_return,
            "message":          a.message,
            "created_at":       str(a.created_at),
        }
        for a in alerts
    ]