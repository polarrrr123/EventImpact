import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from "recharts"

export default function AnalysisPanel({ data }) {
  if (!data) return (
    <div className="analysis-panel empty">
      <p>📈 分析結果將顯示於此</p>
    </div>
  )

  const chartData = [
    { date: "現在", price: data.last_price, type: "actual" },
    ...data.pred_dates.map((d, i) => ({
      date:  d.slice(5),
      price: data.predictions[i],
      type:  "predicted",
    }))
  ]

  const sentimentColor = data.avg_sentiment > 0.05
    ? "#22c55e" : data.avg_sentiment < -0.05
    ? "#ef4444" : "#f59e0b"

  const sentimentLabel = data.avg_sentiment > 0.05
    ? "偏正面 😊" : data.avg_sentiment < -0.05
    ? "偏負面 😟" : "中性 😐"

  return (
    <div className="analysis-panel">
      <h2>📊 {data.company}（{data.ticker}）分析結果</h2>
      <p className="event-tag">🔍 事件：{data.event}</p>

      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-label">目前股價</span>
          <span className="stat-value">NT${data.last_price}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">新聞情緒</span>
          <span className="stat-value" style={{ color: sentimentColor }}>
            {sentimentLabel}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">情緒分數</span>
          <span className="stat-value" style={{ color: sentimentColor }}>
            {data.avg_sentiment.toFixed(4)}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">分析新聞數</span>
          <span className="stat-value">{data.news_count} 則</span>
        </div>
      </div>

      <h3>未來 {data.days} 天預測走勢</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" stroke="#94a3b8" />
          <YAxis
            domain={["auto", "auto"]}
            stroke="#94a3b8"
            tickFormatter={v => `${v}`}
          />
          <Tooltip
            formatter={(v) => [`NT$${v}`, "股價"]}
            contentStyle={{ background: "#1e293b", border: "none" }}
          />
          <ReferenceLine x="現在" stroke="#64748b" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ r: 4, fill: "#6366f1" }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <h3>新聞情緒明細</h3>
      <div className="sentiment-list">
        {data.sentiment_detail.map((item, i) => {
          const color = item.sentiment_score > 0.05
            ? "#22c55e" : item.sentiment_score < -0.05
            ? "#ef4444" : "#f59e0b"
          return (
            <div key={i} className="sentiment-item">
              <span className="sentiment-title">{item.text}</span>
              <span className="sentiment-score" style={{ color }}>
                {item.sentiment_score > 0 ? "+" : ""}
                {item.sentiment_score.toFixed(4)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}