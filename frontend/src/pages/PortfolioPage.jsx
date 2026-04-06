// src/pages/PortfolioPage.jsx
import { useState, useEffect } from "react"
import axios from "axios"
import { useAuth } from "../context/AuthContext"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"

// 常用股票快速選擇
const QUICK_STOCKS = [
  { ticker: "2330.TW", name: "台積電" },
  { ticker: "2317.TW", name: "鴻海" },
  { ticker: "2454.TW", name: "聯發科" },
  { ticker: "2382.TW", name: "廣達" },
  { ticker: "2308.TW", name: "台達電" },
  { ticker: "0050.TW", name: "台灣50" },
  { ticker: "2412.TW", name: "中華電" },
  { ticker: "2881.TW", name: "富邦金" },
]

export default function PortfolioPage() {
  const { token } = useAuth()
  const [portfolio, setPortfolio] = useState([])
  const [loading,   setLoading]   = useState(false)
  const [adding,    setAdding]    = useState(false)
  const [error,     setError]     = useState("")
  const [form,      setForm]      = useState({
    ticker: "", company_name: "", shares: "", buy_price: ""
  })

  const authHeader = { headers: { Authorization: `Bearer ${token}` } }

  // 取得持股清單
  const fetchPortfolio = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API}/portfolio/`, authHeader)
      setPortfolio(res.data)
    } catch {
      setError("無法載入持股資料")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPortfolio() }, [])

  // 新增股票
  const handleAdd = async () => {
    if (!form.ticker || !form.company_name) {
      setError("請填寫股票代號和名稱")
      return
    }
    setError("")
    try {
      await axios.post(`${API}/portfolio/`, {
        ticker:       form.ticker.toUpperCase(),
        company_name: form.company_name,
        shares:       parseFloat(form.shares)    || 0,
        buy_price:    parseFloat(form.buy_price) || 0,
      }, authHeader)
      setForm({ ticker: "", company_name: "", shares: "", buy_price: "" })
      setAdding(false)
      fetchPortfolio()
    } catch (e) {
      setError(e.response?.data?.detail || "新增失敗")
    }
  }

  // 刪除股票
  const handleDelete = async (id) => {
    if (!confirm("確定要移除這支股票嗎？")) return
    try {
      await axios.delete(`${API}/portfolio/${id}`, authHeader)
      fetchPortfolio()
    } catch {
      setError("刪除失敗")
    }
  }

  // 快速選擇股票
  const handleQuickSelect = (stock) => {
    setForm({ ...form, ticker: stock.ticker, company_name: stock.name })
  }

  return (
    <div className="portfolio-page">
      <div className="portfolio-header">
        <h2>📁 我的股票倉庫</h2>
        <button className="btn-primary" onClick={() => setAdding(!adding)}>
          {adding ? "✕ 取消" : "+ 新增股票"}
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {/* 新增表單 */}
      {adding && (
        <div className="add-stock-form">
          <h3>新增持股</h3>

          {/* 快速選擇 */}
          <div className="quick-select">
            <label>快速選擇</label>
            <div className="quick-stocks">
              {QUICK_STOCKS.map(s => (
                <button
                  key={s.ticker}
                  className={`quick-stock-btn ${form.ticker === s.ticker ? "active" : ""}`}
                  onClick={() => handleQuickSelect(s)}
                >
                  {s.name}
                </button>
              ))}
            </div>
          </div>

          <div className="form-row">
            <div className="auth-field">
              <label>股票代號</label>
              <input
                placeholder="例：2330.TW"
                value={form.ticker}
                onChange={e => setForm({ ...form, ticker: e.target.value })}
              />
            </div>
            <div className="auth-field">
              <label>股票名稱</label>
              <input
                placeholder="例：台積電"
                value={form.company_name}
                onChange={e => setForm({ ...form, company_name: e.target.value })}
              />
            </div>
            <div className="auth-field">
              <label>持股數量（選填）</label>
              <input
                type="number"
                placeholder="例：1000"
                value={form.shares}
                onChange={e => setForm({ ...form, shares: e.target.value })}
              />
            </div>
            <div className="auth-field">
              <label>買入價格（選填）</label>
              <input
                type="number"
                placeholder="例：850"
                value={form.buy_price}
                onChange={e => setForm({ ...form, buy_price: e.target.value })}
              />
            </div>
          </div>
          <button className="btn-primary" onClick={handleAdd}>確認新增</button>
        </div>
      )}

      {/* 持股清單 */}
      {loading ? (
        <div className="portfolio-empty">載入中...</div>
      ) : portfolio.length === 0 ? (
        <div className="portfolio-empty">
          <p>📭 還沒有持股</p>
          <p>點擊「新增股票」開始建立你的倉庫</p>
        </div>
      ) : (
        <div className="portfolio-table">
          <div className="portfolio-table-header">
            <span>股票</span>
            <span>代號</span>
            <span>持股數</span>
            <span>買入價</span>
            <span>新增日期</span>
            <span></span>
          </div>
          {portfolio.map(stock => (
            <div key={stock.id} className="portfolio-row">
              <span className="stock-name">{stock.company_name}</span>
              <span className="stock-ticker">{stock.ticker}</span>
              <span>{stock.shares > 0 ? stock.shares.toLocaleString() : "—"}</span>
              <span>{stock.buy_price > 0 ? `NT$${stock.buy_price}` : "—"}</span>
              <span className="stock-date">{stock.added_at.slice(0, 10)}</span>
              <button
                className="btn-delete"
                onClick={() => handleDelete(stock.id)}
              >移除</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}