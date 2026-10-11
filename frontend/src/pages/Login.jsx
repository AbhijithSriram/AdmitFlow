import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { validateEmail } from '../utils/authValidation'

const INPUT_CLASS = 'border border-gray-300 rounded px-3 py-2'

// FR-4: student login — email + password, account lockout after 5 failed attempts.
export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [showSavedNotice, setShowSavedNotice] = useState(Boolean(location.state?.passwordSet))
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setShowSavedNotice(false)
    if (!password || validateEmail(email)) {
      setError('Enter your email and password.')
      return
    }
    setSubmitting(true)
    try {
      await login(email.trim(), password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.response?.data?.error ?? 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // Forgot password reuses the OTP page with purpose=password_reset.
  const handleForgotPassword = async () => {
    setError('')
    setShowSavedNotice(false)
    if (validateEmail(email)) {
      setError('Enter your email above first, then choose "Forgot password".')
      return
    }
    try {
      await authApi.sendOtp({ email: email.trim(), purpose: 'password_reset' })
    } catch (err) {
      // A 429 means a code was sent moments ago: continue to the OTP page rather than blocking.
      if (err.response?.status !== 429) {
        setError(err.response?.data?.error ?? 'Could not send the code. Please try again.')
        return
      }
    }
    navigate('/verify-otp', { state: { email: email.trim(), purpose: 'password_reset' } })
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} noValidate className="w-full max-w-sm flex flex-col gap-4">
        <Link to="/" className="text-sm text-gray-600 underline">
          &larr; Back to home
        </Link>
        <h1 className="text-2xl font-semibold">Log in</h1>

        {showSavedNotice && (
          <p className="text-green-700 text-sm">Password saved. Log in to continue.</p>
        )}

        <label className="flex flex-col gap-1 text-sm font-medium">
          Email
          <input
            type="email"
            autoComplete="username"
            className={INPUT_CLASS}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Password
          <input
            type="password"
            autoComplete="current-password"
            className={INPUT_CLASS}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {error && (
          <p role="alert" className="text-red-600 text-sm">
            {error}
          </p>
        )}

        <button type="submit" disabled={submitting} className="px-4 py-2 rounded bg-black text-white disabled:opacity-50">
          {submitting ? 'Logging in…' : 'Log in'}
        </button>

        <div className="flex justify-between text-sm">
          <button type="button" onClick={handleForgotPassword} className="underline">
            Forgot password?
          </button>
          <Link to="/signup" className="underline">
            Create account
          </Link>
        </div>
      </form>
    </div>
  )
}
