import { useEffect, useRef } from "react"

export default function ChatWindow({ messages, input, loading, onInputChange, onSend, onKeyDown }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="bubble">
              {msg.text.split("\n").map((line, j) => (
                <span key={j}>{line}<br /></span>
              ))}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="bubble loading">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input">
        <textarea
          value={input}
          onChange={e => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="輸入事件與股票，例如：升息對鴻海的影響..."
          rows={2}
        />
        <button onClick={onSend} disabled={loading}>
          {loading ? "分析中..." : "送出"}
        </button>
      </div>
    </div>
  )
}