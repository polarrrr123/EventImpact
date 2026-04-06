// src/pages/AlertPage.jsx
import { useState } from "react"
import axios from "axios"
import { useAuth } from "../context/AuthContext"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"

const ALERT_CONFIG = {
  danger:  { color: "#ef4444", bg: "#450a0a", border: "#991b1b", label: "🔴 高風險",  icon: "🔴" },
  warning: { color: "#f59e0b", bg: "#451a03", border: "#92400e", label: "🟡 需注意",  icon: "🟡" },
  safe:    { color: "#22c55e", bg: "#052e16", border: "#166534", label: "🟢 風險偏低", icon: "🟢" },
  unknown: { color: "#64748b", bg: "#1e293b", border: "#334155", label: "⚪ 無法分析", icon: "⚪" },
}

function ScoreBar({ label, score, maxScore, desc }) {
  const pct = (score / maxScore) * 100
  const color = score >= maxScore * 0.6 ? "#ef4444"
              : score >= maxScore * 0.3 ? "#f59e0b"
              : "#22c55e"
  return (
    <div className="score-bar-item">
      <div className="score-bar-header">
        <span className="score-bar-label">{label}</span>
        <span className="score-bar-value" style={{ color }}>{score}/{maxScore}</span>
      </div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="score-bar-desc">{desc}</span>
    </div>
  )
}

function AlertCard({ alert }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = ALERT_CONFIG[alert.alert_type] || ALERT_CONFIG.unknown

  const chartData = alert.pred_dates
    ? [
        { date: "現在", price: alert.last_price },
        ...alert.pred_dates.map((d, i) => ({
          date:  d.slice(5),
          price: alert.predictions[i],
        }))
      ]
    : []

  return (
    <div className="alert-card" style={{ borderColor: cfg.border, background: cfg.bg }}>
      <div className="alert-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="alert-card-left">
          <span className="alert-icon">{cfg.icon}</span>
          <div>
            <span className="alert-company">{alert.company_name}</span>
            <span className="alert-ticker">{alert.ticker}</span>
          </div>
        </div>
        <div className="alert-card-right">
          <div className="alert-score-circle" style={{ borderColor: cfg.color, color: cfg.color }}>
            {alert.total_score}
          </div>
          <span className="alert-label" style={{ color: cfg.color }}>{cfg.label}</span>
          <span className="alert-expand">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      <p className="alert-message" style={{ color: cfg.color }}>{alert.message}</p>

      {expanded && (
        <div className="alert-detail">
          {/* 評分細節 */}
          {alert.score_detail && (
            <div className="score-breakdown">
              <h4>評分明細</h4>
              <ScoreBar
                label="LSTM 預測跌幅"
                score={alert.score_detail.lstm_pred.score}
                maxScore={40}
                desc={alert.score_detail.lstm_pred.desc}
              />
              <ScoreBar
                label="RSI 超買"
                score={alert.score_detail.rsi.score}
                maxScore={20}
                desc={alert.score_detail.rsi.desc}
              />
              <ScoreBar
                label="均線死叉"
                score={alert.score_detail.moving_avg.score}
                maxScore={20}
                desc={alert.score_detail.moving_avg.desc}
              />
              <ScoreBar
                label="新聞情緒"
                score={alert.score_detail.sentiment.score}
                maxScore={20}
                desc={alert.score_detail.sentiment.desc}
              />
            </div>
          )}

          {/* 預測走勢圖 */}
          {chartData.length > 0 && (
            <div className="alert-chart">
              <h4>未來5日預測走勢</h4>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <YAxis domain={["auto", "auto"]} stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={v => [`NT$${v}`, "股價"]}
                    contentStyle={{ background: "#1e293b", border: "none" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke={cfg.color}
                    strokeWidth={2}
                    dot={{ r: 4, fill: cfg.color }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AlertPage() {
  const { token }   = useAuth()
  const [alerts,    setAlerts]   = useState([])
  const [loading,   setLoading]  = useState(false)
  const [scanned,   setScanned]  = useState(false)
  const [error,     setError]    = useState("")

  const authHeader = { headers: { Authorization: `Bearer ${token}` } }

  const handleScan = async () => {
    setLoading(true)
    setError("")
    try {
      const res = await axios.get(`${API}/alerts/scan`, authHeader)
      setAlerts(res.data.alerts)
      setScanned(true)
    } catch (e) {
      setError(e.response?.data?.detail || "掃描失敗，請確認倉庫中有持股")
    } finally {
      setLoading(false)
    }
  }

  const dangerCount  = alerts.filter(a => a.alert_type === "danger").length
  const warningCount = alerts.filter(a => a.alert_type === "warning").length
  const safeCount    = alerts.filter(a => a.alert_type === "safe").length

  return (
    <div className="alert-page">
      <div className="alert-header">
        <div>
          <h2>🚨 持股預警系統</h2>
          <p className="alert-subtitle">綜合 LSTM預測、RSI、均線、新聞情緒進行風險評估</p>
        </div>
        <button className="btn-primary" onClick={handleScan} disabled={loading}>
          {loading ? "掃描中..." : "🔍 立即掃描"}
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {loading && (
        <div className="alert-loading">
          <p>正在分析所有持股，每支股票約需 30-60 秒...</p>
          <div className="loading-bar">
            <div className="loading-bar-fill" />
          </div>
        </div>
      )}

      {scanned && !loading && (
        <>
          {/* 統計摘要 */}
          <div className="alert-summary">
            <div className="summary-card danger">
              <span className="summary-num">{dangerCount}</span>
              <span>高風險</span>
            </div>
            <div className="summary-card warning">
              <span className="summary-num">{warningCount}</span>
              <span>需注意</span>
            </div>
            <div className="summary-card safe">
              <span className="summary-num">{safeCount}</span>
              <span>風險偏低</span>
            </div>
          </div>

          {/* 預警清單 */}
          <div className="alert-list">
            {alerts.length === 0
              ? <p className="portfolio-empty">倉庫中沒有持股，請先前往「我的倉庫」新增股票</p>
              : alerts.map((a, i) => <AlertCard key={i} alert={a} />)
            }
          </div>
        </>
      )}

      {!scanned && !loading && (
        <div className="alert-empty">
          <p>點擊「立即掃描」開始分析你的持股風險</p>
          <p style={{ fontSize: "13px", marginTop: "8px", color: "#475569" }}>
            系統會分析倉庫中所有股票的 LSTM預測、RSI、均線狀況與新聞情緒
          </p>
        </div>
      )}
    </div>
  )
}