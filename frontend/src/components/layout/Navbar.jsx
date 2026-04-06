// src/components/layout/Navbar.jsx
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../../context/AuthContext"

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">📊 EventImpact</Link>
        <span>新聞事件驅動股價分析</span>
      </div>
      <div className="navbar-links">
        {user ? (
          <>
            <Link to="/">分析</Link>
            <Link to="/portfolio">我的倉庫</Link>
            <span className="navbar-user">👤 {user.username}</span>
            <button onClick={handleLogout} className="btn-logout">登出</button>
          </>
        ) : (
          <>
            <Link to="/login">登入</Link>
            <Link to="/register">註冊</Link>
            <Link to="/alerts">預警</Link>
          </>
        )}
      </div>
    </nav>
  )
}