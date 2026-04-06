// src/pages/LoginPage.jsx
import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import axios from "axios"
import { useAuth } from "../context/AuthContext"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function LoginPage() {
  const [form,    setForm]    = useState({ username: "", password: "" })
  const [error,   setError]   = useState("")
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()

  const handleSubmit = async () => {
    if (!form.username || !form.password) {
      setError("請填寫所有欄位")
      return
    }
    setLoading(true)
    setError("")
    try {
      // OAuth2 格式需要 FormData
      const params = new URLSearchParams()
      params.append("username", form.username)
      params.append("password", form.password)

      const res = await axios.post(`${API}/auth/login`, params)
      const token = res.data.access_token

      // 取得使用者資料
      const meRes = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      login(token, meRes.data)
      navigate("/")
    } catch (e) {
      setError(e.response?.data?.detail || "登入失敗，請確認帳號密碼")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>📊 登入 EventImpact</h2>
        <p className="auth-subtitle">輸入帳號密碼開始分析</p>

        {error && <div className="auth-error">{error}</div>}

        <div className="auth-field">
          <label>帳號</label>
          <input
            type="text"
            placeholder="輸入帳號"
            value={form.username}
            onChange={e => setForm({ ...form, username: e.target.value })}
            onKeyDown={e => e.key === "Enter" && handleSubmit()}
          />
        </div>

        <div className="auth-field">
          <label>密碼</label>
          <input
            type="password"
            placeholder="輸入密碼"
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            onKeyDown={e => e.key === "Enter" && handleSubmit()}
          />
        </div>

        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "登入中..." : "登入"}
        </button>

        <p className="auth-switch">
          還沒有帳號？<Link to="/register">立即註冊</Link>
        </p>
      </div>
    </div>
  )
}