import { useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import axios from "axios"
import { AuthProvider, useAuth } from "./context/AuthContext"
import Navbar from "./components/layout/Navbar"
import ChatWindow from "./components/ChatWindow"
import AnalysisPanel from "./components/AnalysisPanel"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import PortfolioPage from "./pages/PortfolioPage"
import "./App.css"
import AlertPage from "./pages/AlertPage"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"
const SESSION_ID = "user_" + Math.random().toString(36).slice(2, 8)

function ProtectedRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" />
}

function MainPage() {
  const [messages, setMessages]         = useState([{
    role: "assistant",
    text: "你好！我是 EventImpact 股市分析助理 📊\n請描述你想分析的事件與股票，例如：\n「美中關稅對台積電未來5天的影響」",
  }])
  const [input, setInput]               = useState("")
  const [loading, setLoading]           = useState(false)
  const [analysisData, setAnalysisData] = useState(null)

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput("")
    setMessages(prev => [...prev, { role: "user", text: userMsg }])
    setLoading(true)
    try {
      const res  = await axios.post(`${API}/chat`, {
        session_id: SESSION_ID,
        message:    userMsg,
      })
      const data = res.data
      setMessages(prev => [...prev, { role: "assistant", text: data.reply }])
      if (data.type === "analysis" && data.data) setAnalysisData(data.data)
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "❌ 連線失敗，請確認後端是否在運行。",
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app-body">
      <ChatWindow
        messages={messages}
        input={input}
        loading={loading}
        onInputChange={setInput}
        onSend={sendMessage}
        onKeyDown={handleKeyDown}
      />
      <AnalysisPanel data={analysisData} />
    </div>
  )
}

function AppLayout() {
  return (
    <div className="app">
      <Navbar />
      <Routes>
        <Route path="/login"     element={<LoginPage />} />
        <Route path="/register"  element={<RegisterPage />} />
        <Route path="/" element={
          <ProtectedRoute><MainPage /></ProtectedRoute>
        } />
        <Route path="/portfolio" element={
          <ProtectedRoute><PortfolioPage /></ProtectedRoute>
        } />
        <Route path="/alerts" element={
          <ProtectedRoute><AlertPage /></ProtectedRoute>
        } />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </AuthProvider>
  )
}