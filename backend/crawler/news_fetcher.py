# crawler/news_fetcher.py
import requests
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def fetch_cnyes_news(keyword: str, max_pages: int = 2) -> pd.DataFrame:
    """
    從 Google News RSS 抓取關鍵字新聞
    max_pages 保留參數相容性，RSS 一次回傳約 20 則
    """
    articles = []

    url = (
        f"https://news.google.com/rss/search"
        f"?q={requests.utils.quote(keyword)}"
        f"&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        print(f"HTTP 狀態碼：{resp.status_code}")

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        print(f"[✓] 找到 {len(items)} 則新聞")

        for item in items:
            title   = item.findtext("title", "").strip()
            pub     = item.findtext("pubDate", "").strip()
            link    = item.findtext("link", "").strip()
            source  = item.findtext("source", "").strip()

            if not title:
                continue

            articles.append({
                "title":      title,
                "published":  pub,
                "url":        link,
                "source":     source,
                "keyword":    keyword,
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    except Exception as e:
        print(f"[✗] 失敗：{e}")

    df = pd.DataFrame(articles)
    print(f"[✓] 共抓到 {len(df)} 則「{keyword}」相關新聞")
    return df


if __name__ == "__main__":
    df = fetch_cnyes_news("美中關稅", max_pages=2)
    if not df.empty:
        print(df[["title", "published", "source"]].head(10).to_string())