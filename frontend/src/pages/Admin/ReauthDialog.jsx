import { useState } from 'react'
import { adminApi } from '../../api/client'
import { errorMessage } from './adminUtils'

// Sign in again WITHOUT leaving the page. Long admin forms (the test editor) use this when the
// session has expired, so the work on screen survives: the parent keeps its state and retries the
// action once onSignedIn runs. (Navigating to /admin/auth instead throws all of it away.)
// saving: a save was refused and runs again after sign-in. When false (the keep-alive found the session
// gone while nothing was being saved) the dialog does not promise a save.
export default function ReauthDialog({ email: initialEmail = '', saving = true, onSignedIn, onCancel }) {
  const [email, setEmail] = useState(initialEmail)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await adminApi.login({ email: email.trim(), password })
      onSignedIn()
    } catch (err) {
      setError(errorMessage(err))
      setBusy(false)
    }
  }

  const field = 'border border-slate-400 rounded-md px-3 py-2 font-normal focus:outline-2 focus:outline-indigo-600'
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <form onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="reauth-title"
        className="bg-white rounded-lg w-full max-w-sm p-6 flex flex-col gap-4">
        <div>
          <h2 id="reauth-title" className="text-lg font-semibold text-slate-900">{saving ? 'Sign in again to save' : 'Sign in again'}</h2>
          <p className="text-sm text-slate-700 mt-1">
            {saving
              ? 'Your session timed out. Nothing on this page has been lost: sign in and your work is saved straight away.'
              : 'Your session has ended. Nothing on this page has been lost: sign in to carry on where you were.'}
          </p>
        </div>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Email
          <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} className={field} />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Password
          <input type="password" autoComplete="current-password" required autoFocus value={password}
            onChange={(e) => setPassword(e.target.value)} className={field} />
        </label>
        {error && <p role="alert" className="text-sm font-medium text-red-700">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} disabled={busy}
            className="text-sm border border-slate-400 rounded-md px-3 py-2 hover:bg-slate-100 disabled:opacity-50">
            Not now
          </button>
          <button type="submit" disabled={busy || !email || !password}
            className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700 disabled:opacity-50">
            {busy ? 'Signing in…' : saving ? 'Sign in and save' : 'Sign in'}
          </button>
        </div>
      </form>
    </div>
  )
}
