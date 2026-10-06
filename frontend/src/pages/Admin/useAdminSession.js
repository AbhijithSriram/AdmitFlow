import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../../api/client'

/**
 * Admin session state, deliberately separate from the student AuthContext: different
 * cookie, different role (SRD FR-7.1). status: 'loading' | 'authed' | 'anon'.
 */
export function useAdminSession() {
  const [status, setStatus] = useState('loading')
  const [admin, setAdmin] = useState(null)

  useEffect(() => {
    let cancelled = false
    adminApi
      .me()
      .then((res) => {
        if (cancelled) return
        setAdmin(res.data.data.admin)
        setStatus('authed')
      })
      .catch(() => !cancelled && setStatus('anon'))
    return () => {
      cancelled = true
    }
  }, [])

  const expire = useCallback(() => {
    setAdmin(null)
    setStatus('anon')
  }, [])

  const signOut = useCallback(async () => {
    try {
      await adminApi.logout()
    } finally {
      expire()
    }
  }, [expire])

  return { status, admin, signOut, expire }
}
