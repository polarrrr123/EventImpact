// src/pages/RegisterPage.jsx
import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import axios from "axios"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function RegisterPage() {
  const [form,    setForm]    = useState({ username: "", email: "", password: "", confirm: "" })
  const [error,   setError]   = useState("")
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async () => {
    if (!form.username || !form.email || !form.password) {
      setError("請填寫所有欄位")
      return
    }
    if (form.password !== form.confirm) {
      setError("兩次密碼不一致")
      return
    }
    setLoading(true)
    setError("")
    try {
      await axios.post(`${API}/auth/register`, {
        username: form.username,
        email:    form.email,
        password: form.password,
      })
      navigate("/login")
    } catch (e) {
      setError(e.response?.data?.detail || "註冊失敗")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>📊 註冊 EventImpact</h2>
        <p className="auth-subtitle">建立帳號開始使用</p>

        {error && <div className="auth-error">{error}</div>}

        {[
          { label: "帳號",    key: "username", type: "text",     placeholder: "設定帳號" },
          { label: "Email",  key: "email",    type: "email",    placeholder: "輸入 Email" },
          { label: "密碼",    key: "password", type: "password", placeholder: "設定密碼" },
          { label: "確認密碼", key: "confirm",  type: "password", placeholder: "再輸入一次密碼" },
        ].map(f => (
          <div className="auth-field" key={f.key}>
            <label>{f.label}</label>
            <input
              type={f.type}
              placeholder={f.placeholder}
              value={form[f.key]}
              onChange={e => setForm({ ...form, [f.key]: e.target.value })}
            />
          </div>
        ))}

        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "註冊中..." : "註冊"}
        </button>

        <p className="auth-switch">
          已有帳號？<Link to="/login">立即登入</Link>
        </p>
      </div>
    </div>
  )
}