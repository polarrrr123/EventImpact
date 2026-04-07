---
title: EventImpact API
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

<div align="center">

#  EventImpact

### 新聞事件驅動的 AI 股票分析與預警平台
### AI-Powered News-Driven Stock Analysis & Alert Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-event--impact.vercel.app-6366f1?style=for-the-badge)](https://event-impact.vercel.app)
[![API](https://img.shields.io/badge/API-HuggingFace%20Spaces-ff9d00?style=for-the-badge)](https://polarrrr123-eventimpact-api.hf.space)
[![GitHub](https://img.shields.io/badge/GitHub-polarrrr123-181717?style=for-the-badge&logo=github)](https://github.com/polarrrr123/EventImpact)

</div>

---

## 🇹🇼 中文版

### 專案簡介

EventImpact 是一個結合自然語言處理、深度學習與全端工程的 AI 股票分析平台。使用者透過對話式介面輸入事件與股票，系統自動爬取新聞、分析情緒、預測股價，並提供個人化的持股預警服務。

### 功能特色

- **對話式 AI 介面** — 自然語言輸入，Groq (Llama 3.1) 自動解析事件與股票標的
- **即時新聞爬蟲** — Google News RSS 抓取最新相關新聞（100+ 則）
- **FinBERT 情緒分析** — 金融專用 BERT 模型，中文新聞翻譯後分析正負面情緒
- **LSTM 深度學習預測** — 雙層 LSTM 模型，結合技術指標預測未來 5 日股價走勢
- **使用者認證系統** — JWT 登入/註冊，bcrypt 密碼加密
- **個人股票倉庫** — 持股管理，資料儲存於雲端資料庫
- **綜合評分預警系統** — LSTM 預測跌幅 + RSI + 均線死叉 + 新聞情緒，100 分制風險評估

###  系統架構
使用者輸入自然語言
↓
Groq (Llama 3.1) 語意解析
↓
對話管理器（收集事件、股票、天數）
↓
┌─────────────────────────────────┐
│  Google News RSS 爬蟲            │
│  FinBERT 情緒分析                │
│  yfinance 股價資料               │
│  技術指標特徵工程                 │
└─────────────────────────────────┘
↓
LSTM 深度學習預測模型
↓
React 前端視覺化 + 預警系統

###  技術架構

| 層級 | 技術 |
|------|------|
| 前端 | React + Vite + Recharts + React Router |
| 後端 | FastAPI + Uvicorn |
| 語意理解 | Groq API (Llama 3.1-8b-instant) |
| 情緒分析 | FinBERT (ProsusAI/finbert) |
| 預測模型 | LSTM (PyTorch, 2-layer, hidden=64) |
| 股價資料 | yfinance |
| 新聞資料 | Google News RSS |
| 認證 | JWT + bcrypt |
| 資料庫 | SQLite (本地) / PostgreSQL (Supabase) |
| ORM | SQLAlchemy |
| 部署 | HuggingFace Spaces (後端) + Vercel (前端) |

###  模型說明

#### LSTM 預測模型
- 架構：2 層 LSTM（hidden_size=64）+ Fully Connected Layer
- 輸入：過去 20 天的 9 個特徵（技術指標 + 情緒分數）
- 輸出：未來 N 天收盤價預測
- 訓練：80% 訓練 / 20% 測試，80 epochs，Adam optimizer

#### 特徵工程
| 特徵 | 說明 |
|------|------|
| return / return_2d / return_5d | 1日、2日、5日報酬率 |
| ma5_bias / ma10_bias | 移動平均乖離率 |
| volatility | 5日報酬率標準差 |
| vol_change | 成交量變化率 |
| rsi | 14日相對強弱指標 |
| sentiment | FinBERT 新聞情緒分數 |

#### 預警評分系統（滿分 100）
| 指標 | 權重 | 說明 |
|------|------|------|
| LSTM 預測跌幅 | 40分 | 預測最大跌幅越大分數越高 |
| RSI 超買 | 20分 | RSI > 70 觸發 |
| 均線死叉 | 20分 | MA5 跌破 MA10 |
| 新聞情緒 | 20分 | FinBERT 負面情緒越強分數越高 |

> 總分 ≥ 60 → (紅色) 高風險｜總分 ≥ 35 → (黃色) 需注意｜總分 < 35 → (綠色) 風險偏低

###  本地開發

#### 後端
```bash
conda create -n event_impact python=3.11
conda activate event_impact
pip install -r requirements_hf.txt
cp .env.example .env  # 填入 GROQ_API_KEY 和 DATABASE_URL
cd backend/api
uvicorn main:app --reload --port 8000
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

#### 環境變數
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=your_database_url
SECRET_KEY=your_jwt_secret_key

###  專案結構
EventImpact/
├── backend/
│   ├── api/
│   │   ├── main.py                  # FastAPI 主程式
│   │   ├── auth.py                  # JWT 認證
│   │   ├── intent_parser.py         # Groq 語意解析
│   │   ├── conversation_manager.py  # 對話狀態管理
│   │   └── route/
│   │       ├── auth_routes.py       # 註冊/登入 API
│   │       ├── portfolio_routes.py  # 股票倉庫 API
│   │       └── alert_routes.py      # 預警掃描 API
│   ├── crawler/
│   │   ├── news_fetcher.py          # Google News 爬蟲
│   │   └── stock_fetcher.py         # yfinance 股價抓取
│   ├── model/
│   │   ├── lstm_model.py            # LSTM 預測模型
│   │   └── evaluator.py             # 模型評估與回測
│   ├── pipeline.py                  # 主分析流程
│   └── database.py                  # SQLAlchemy ORM
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── context/AuthContext.jsx
│       ├── components/
│       │   ├── ChatWindow.jsx
│       │   ├── AnalysisPanel.jsx
│       │   └── layout/Navbar.jsx
│       └── pages/
│           ├── LoginPage.jsx
│           ├── RegisterPage.jsx
│           ├── PortfolioPage.jsx
│           └── AlertPage.jsx
├── Dockerfile
├── app.py
└── requirements_hf.txt

---

##  English Version

### Overview

EventImpact is a full-stack AI stock analysis platform combining NLP, deep learning, and web engineering. Users interact through a conversational interface to analyze how news events impact specific stocks, with personalized portfolio monitoring and alert services.

###  Features

-  **Conversational AI Interface** — Natural language input, auto-parsed by Groq (Llama 3.1)
-  **Real-time News Crawler** — Google News RSS fetching 100+ relevant articles
-  **FinBERT Sentiment Analysis** — Finance-domain BERT model for news sentiment scoring
-  **LSTM Deep Learning Prediction** — 2-layer LSTM predicting 5-day stock price trends
-  **User Authentication** — JWT login/register with bcrypt password hashing
-  **Personal Stock Portfolio** — Holdings management with persistent cloud storage
-  **Composite Alert System** — Risk scoring via LSTM + RSI + Moving Average + Sentiment

###  Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + Recharts + React Router |
| Backend | FastAPI + Uvicorn |
| NLU | Groq API (Llama 3.1-8b-instant) |
| Sentiment | FinBERT (ProsusAI/finbert) |
| Prediction | LSTM (PyTorch, 2-layer, hidden=64) |
| Market Data | yfinance |
| News Data | Google News RSS |
| Auth | JWT + bcrypt |
| Database | SQLite (local) / PostgreSQL (Supabase) |
| ORM | SQLAlchemy |
| Deployment | HuggingFace Spaces (API) + Vercel (Frontend) |

###  Alert Scoring System (Max 100pts)

| Signal | Weight | Trigger |
|--------|--------|---------|
| LSTM predicted drop | 40pts | Larger predicted decline = higher score |
| RSI overbought | 20pts | RSI > 70 |
| Death cross | 20pts | MA5 crosses below MA10 |
| News sentiment | 20pts | Stronger negative sentiment = higher score |

> Score ≥ 60 → (Red) High Risk｜Score ≥ 35 → (Yellow) Warning｜Score < 35 → (Green) Safe

###  Quick Start
```bash
# Backend
conda create -n event_impact python=3.11 && conda activate event_impact
pip install -r requirements_hf.txt
cp .env.example .env
cd backend/api && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

---

##  Author

**Fu Yu-Cheng (傅裕成)**  
M.S. Student, Information Management, National Chung Hsing University  
[GitHub](https://github.com/polarrrr123)