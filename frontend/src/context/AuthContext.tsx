import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import type { AuthUser } from '../types'

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  login: (token: string, user: AuthUser) => void
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  isLoading: false,
})

function loadFromStorage(): { user: AuthUser | null; token: string | null } {
  try {
    const storedToken = localStorage.getItem('auth_token')
    const storedUser = localStorage.getItem('auth_user')
    if (storedToken && storedUser) {
      return { user: JSON.parse(storedUser) as AuthUser, token: storedToken }
    }
  } catch {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }
  return { user: null, token: null }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = loadFromStorage()
  const [user, setUser] = useState<AuthUser | null>(initial.user)
  const [token, setToken] = useState<string | null>(initial.token)
  // isLoading is true only on initial page-load when a token exists (verifying it)
  const [isLoading, setIsLoading] = useState<boolean>(!!initial.token)

  // Re-runs whenever token changes (on page load AND after fresh login/register)
  // This guarantees analyses_used is always the live value from the DB
  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

    axios.get<AuthUser>('/api/auth/me')
      .then(({ data }) => {
        setUser((prev) => {
          const updated = prev ? { ...prev, ...data } : data
          localStorage.setItem('auth_user', JSON.stringify(updated))
          return updated
        })
      })
      .catch(() => {
        // Token expired or invalid — clear session
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_user')
        setToken(null)
        setUser(null)
        delete axios.defaults.headers.common['Authorization']
      })
      .finally(() => setIsLoading(false))
  }, [token]) // ← depends on token, re-fetches on every login

  function login(newToken: string, newUser: AuthUser) {
    setToken(newToken)
    setUser(newUser)
    localStorage.setItem('auth_token', newToken)
    localStorage.setItem('auth_user', JSON.stringify(newUser))
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    // useEffect above will fire because token changed → fetches live stats
  }

  function logout() {
    setToken(null)
    setUser(null)
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    delete axios.defaults.headers.common['Authorization']
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
