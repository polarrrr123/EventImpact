// src/pages/AuthCallbackPage.jsx
import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"
import { useAuth } from "../context/AuthContext"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function AuthCallbackPage() {
  const { login }  = useAuth()
  const navigate   = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token  = params.get("token")

    if (!token) {
      navigate("/login")
      return
    }

    // 用 token 取得使用者資訊
    axios.get(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => {
      login(token, res.data)
      navigate("/")
    }).catch(() => {
      navigate("/login")
    })
  }, [])

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      color: "#94a3b8",
      fontSize: "16px"
    }}>
      登入中，請稍候...
    </div>
  )
}