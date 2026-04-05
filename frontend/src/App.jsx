import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ChatWindow from "./components/ChatWindow"
import AnalysisPanel from "./components/AnalysisPanel"
import "./App.css"

const API = "http://localhost:8000"
const SESSION_ID = "user_" + Math.random().toString(36).slice(2, 8)

export default function App() {
  const [messages, setMessages]   = useState([
    {
      role: "assistant",
      text: "你好！我是 EventImpact 股市分析助理 📊\n請描述你想分析的事件與股票，例如：\n「美中關稅對台積電未來5天的影響」",
    }
  ])
  const [input, setInput]         = useState("")
  const [loading, setLoading]     = useState(false)
  const [analysisData, setAnalysisData] = useState(null)

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput("")
    setMessages(prev => [...prev, { role: "user", text: userMsg }])
    setLoading(true)

    try {
      const res = await axios.post(`${API}/chat`, {
        session_id: SESSION_ID,
        message:    userMsg,
      })
      const data = res.data

      setMessages(prev => [...prev, { role: "assistant", text: data.reply }])

      if (data.type === "analysis" && data.data) {
        setAnalysisData(data.data)
      }
    } catch (e) {
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
    <div className="app">
      <header className="app-header">
        <h1>📊 EventImpact</h1>
        <span>新聞事件驅動股價分析</span>
      </header>
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
    </div>
  )
}