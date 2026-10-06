import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { adminApi } from '../../api/client'
import { errorMessage } from './adminUtils'
import { useAdminSession } from './useAdminSession'

// FR-7.1: admin login served at a non-public path, isolated session from students.
export default function AdminLogin() {
  const navigate = useNavigate()
  const { status } = useAdminSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Keep this page out of search engines.
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    document.head.appendChild(meta)
    return () => meta.remove()
  }, [])

  if (status === 'authed') return <Navigate to="/admin/dashboard" replace />

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await adminApi.login({ email: email.trim(), password })
      navigate('/admin/dashboard', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-100">
      <form onSubmit={onSubmit} className="w-full max-w-sm flex flex-col gap-4 bg-white border border-slate-200 rounded-lg p-7">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Staff sign in</h1>
          <p className="text-sm text-slate-600 mt-1">For college admissions staff only.</p>
        </div>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Email
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-slate-400 rounded-md px-3 py-2 font-normal focus:outline-2 focus:outline-indigo-600"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border border-slate-400 rounded-md px-3 py-2 font-normal focus:outline-2 focus:outline-indigo-600"
          />
        </label>

        {error && (
          <p role="alert" className="text-sm font-medium text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !email || !password}
          className="bg-slate-900 text-white rounded-md py-2 font-medium hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
