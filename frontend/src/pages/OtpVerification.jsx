import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'

const RESEND_COOLDOWN_SECONDS = 60
const STORAGE_KEY = 'admitflow_otp_context'

// Router state is lost on refresh, so mirror it in sessionStorage (per-tab, cleared on close).
function readContext(locationState) {
  if (locationState?.email) return locationState
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) ?? {}
  } catch {
    return {}
  }
}

// FR-3: OTP verification — 6-digit code, 10-minute expiry, then password setup.
export default function OtpVerification() {
  const location = useLocation()
  const navigate = useNavigate()
  const { email, purpose = 'email_verification' } = readContext(location.state)

  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS)

  useEffect(() => {
    if (!email) return
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ email, purpose }))
    } catch {
      // storage unavailable: refresh will just send the user back to start
    }
  }, [email, purpose])

  useEffect(() => {
    if (cooldown <= 0) return undefined
    const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  if (!email) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 text-center">
        <p>
          We don&apos;t know which email to verify.{' '}
          <Link to="/signup" className="underline">
            Start again
          </Link>
        </p>
      </div>
    )
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setInfo('')
    if (!/^\d{6}$/.test(otp)) {
      setError('Enter the 6-digit code from your email.')
      return
    }
    setSubmitting(true)
    try {
      await authApi.verifyOtp({ email, otp, purpose })
      navigate('/set-password', { state: { email, purpose } })
    } catch (err) {
      setError(err.response?.data?.error ?? 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleResend = async () => {
    setError('')
    setInfo('')
    try {
      await authApi.sendOtp({ email, purpose })
      setInfo('A new code has been sent.')
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch (err) {
      setError(err.response?.data?.error ?? 'Could not resend the code.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} noValidate className="w-full max-w-sm flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">
          {purpose === 'password_reset' ? 'Enter your reset code' : 'Verify your email'}
        </h1>
        <p className="text-sm text-gray-600">
          Enter the 6-digit code we sent to <b>{email}</b>. It expires in 10 minutes.
        </p>

        <input
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          aria-label="6-digit verification code"
          className="border border-gray-300 rounded px-3 py-2 text-center text-xl tracking-widest"
          value={otp}
          onChange={(event) => setOtp(event.target.value.replace(/\D/g, ''))}
        />

        {error && <p className="text-red-600 text-sm">{error}</p>}
        {info && <p className="text-green-700 text-sm">{info}</p>}

        <button type="submit" disabled={submitting} className="px-4 py-2 rounded bg-black text-white disabled:opacity-50">
          {submitting ? 'Verifying…' : 'Verify'}
        </button>
        <button
          type="button"
          onClick={handleResend}
          disabled={cooldown > 0}
          className="text-sm underline disabled:no-underline disabled:text-gray-500"
        >
          {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
        </button>
      </form>
    </div>
  )
}
