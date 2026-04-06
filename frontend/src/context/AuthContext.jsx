// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from "react"

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [token, setToken]   = useState(localStorage.getItem("token") || null)
  const [user,  setUser]    = useState(JSON.parse(localStorage.getItem("user") || "null"))

  const login = (accessToken, userData) => {
    setToken(accessToken)
    setUser(userData)
    localStorage.setItem("token", accessToken)
    localStorage.setItem("user",  JSON.stringify(userData))
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem("token")
    localStorage.removeItem("user")
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}