import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiClient, authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [student, setStudent] = useState(null)
  // True until the first /me check finishes, so protected pages don't flash a redirect on refresh.
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    apiClient
      .get('/api/auth/me')
      .then(({ data }) => {
        if (!cancelled) setStudent(data.data.student)
      })
      .catch(() => {
        // 401 just means "not logged in" — nothing to restore.
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // The API client fires this when a request comes back 401 mid-session (idle timeout).
  useEffect(() => {
    const onExpired = () => setStudent(null)
    window.addEventListener('admitflow:session-expired', onExpired)
    return () => window.removeEventListener('admitflow:session-expired', onExpired)
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await authApi.login({ email, password })
    setStudent(data.data.student)
    return data.data.student
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      // Clear local state even if the request failed (e.g. session already expired).
      setStudent(null)
    }
  }, [])

  const value = useMemo(
    () => ({ student, loading, isAuthenticated: Boolean(student), login, logout }),
    [student, loading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
