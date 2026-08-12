import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import type { AuthUser } from '../types'

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  isLoading: boolean
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  token: null,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: async () => {},
  isLoading: true,
})

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount, check local storage for a saved token
  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token')
    if (savedToken) {
      setToken(savedToken)
      axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`
      fetchBackendUser(savedToken)
    } else {
      setIsLoading(false)
    }
  }, [])

  async function fetchBackendUser(accessToken: string) {
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    try {
      axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
      const { data } = await axios.get<AuthUser>(`${BASE}/auth/me`)
      setUser(data)
    } catch {
      // Token expired or invalid — clear it
      setUser(null)
      setToken(null)
      localStorage.removeItem('auth_token')
      delete axios.defaults.headers.common['Authorization']
    } finally {
      setIsLoading(false)
    }
  }

  async function login(email: string, password: string) {
    const { data } = await axios.post(`${BASE}/auth/login`, { email, password })
    const { token: newToken, ...userData } = data
    localStorage.setItem('auth_token', newToken)
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    setToken(newToken)
    setUser(userData)
  }

  async function register(name: string, email: string, password: string) {
    const { data } = await axios.post(`${BASE}/auth/register`, { name, email, password })
    const { token: newToken, ...userData } = data
    localStorage.setItem('auth_token', newToken)
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    setToken(newToken)
    setUser(userData)
  }

  function logout() {
    setUser(null)
    setToken(null)
    localStorage.removeItem('auth_token')
    delete axios.defaults.headers.common['Authorization']
  }

  async function refreshUser() {
    if (!token) return
    try {
      const { data } = await axios.get<AuthUser>(`${BASE}/auth/me`)
      setUser((prev) => (prev ? { ...prev, ...data } : data))
    } catch {
      // silently fail
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, refreshUser, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}