# crawler/stock_fetcher.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

TICKER_NAME = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "0050.TW": "台灣50",
}

def fetch_stock_history(ticker: str, days: int = 120) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=days)
    #自動補上 .TW
    if ticker.isdigit():
        ticker = ticker + ".TW"
    elif "." not in ticker:
        ticker = ticker + ".TW"
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "date"
    df = df.dropna()

    print(f"[✓] {ticker} 抓到 {len(df)} 筆資料")
    return df