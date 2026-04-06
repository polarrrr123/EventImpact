---
title: EventImpact API
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 📊 EventImpact
（以下是原本的內容）
...

![EventImpact Preview](docs/preview.png)
# EventImpact

> 新聞事件驅動的台股股價預測系統

輸入自然語言（例如「美中關稅對台積電未來5天的影響」），系統自動爬取新聞、進行情緒分析、預測股價走勢。

## 功能
- 對話式 AI 介面（自然語言輸入）
- Google News 即時新聞爬蟲
- FinBERT 金融情緒分析
- GradientBoosting + 技術指標股價預測
- React 視覺化儀表板

## 技術架構
| 層級 | 技術 |
|------|------|
| 前端 | React + Vite + Recharts |
| 後端 | FastAPI |
| NLP  | FinBERT + Groq (Llama 3.1) |
| 預測 | GradientBoostingRegressor |
| 資料 | yfinance + Google News RSS |

## 快速開始

### 後端
```bash
conda create -n event_impact python=3.11
conda activate event_impact
pip install -r requirements.txt
cp .env.example .env  # 填入 GROQ_API_KEY
cd backend/api
uvicorn main:app --reload --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

## 環境變數
複製 `.env.example` 為 `.env` 並填入：
```
GROQ_API_KEY=your_key_here
```