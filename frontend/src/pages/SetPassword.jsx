import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import { validatePassword } from '../utils/authValidation'

const INPUT_CLASS = 'border border-gray-300 rounded px-3 py-2'

// FR-3: set password after OTP verification (min 8 chars, 1 number, 1 special char).
export default function SetPassword() {
  const location = useLocation()
  const navigate = useNavigate()
  const purpose = location.state?.purpose
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  // Landing here directly (no OTP step in this tab) can't succeed: the server needs the OTP proof.
  if (!purpose) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 text-center">
        <p>
          Please verify your email first.{' '}
          <Link to="/signup" className="underline">
            Register
          </Link>{' '}
          or{' '}
          <Link to="/login" className="underline">
            log in
          </Link>
          .
        </p>
      </div>
    )
  }

  // Cancelling just abandons this step; the server-side OTP proof expires on its own.
  const handleCancel = () => {
    try {
      sessionStorage.removeItem('admitflow_otp_context')
    } catch {
      // ignore: storage unavailable
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = {}
    const passwordError = validatePassword(password)
    if (passwordError) found.password = passwordError
    if (confirmPassword !== password) found.confirmPassword = 'Passwords do not match.'
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setSubmitting(true)
    try {
      await authApi.setPassword({ password, confirm_password: confirmPassword })
      try {
        sessionStorage.removeItem('admitflow_otp_context')
      } catch {
        // ignore: storage unavailable
      }
      navigate('/login', { state: { passwordSet: true }, replace: true })
    } catch (err) {
      const body = err.response?.data
      const fieldMap = { confirm_password: 'confirmPassword' }
      const field = fieldMap[body?.field] ?? body?.field ?? 'form'
      setErrors({ [field]: body?.error ?? 'Something went wrong. Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} noValidate className="w-full max-w-sm flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">
          {purpose === 'password_reset' ? 'Choose a new password' : 'Set a password'}
        </h1>
        <p className="text-sm text-gray-600">At least 8 characters, with a number and a special character.</p>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Password
          <input
            type="password"
            autoComplete="new-password"
            className={INPUT_CLASS}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {errors.password && <span className="text-red-600 font-normal">{errors.password}</span>}
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Confirm password
          <input
            type="password"
            autoComplete="new-password"
            className={INPUT_CLASS}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
          {errors.confirmPassword && <span className="text-red-600 font-normal">{errors.confirmPassword}</span>}
        </label>

        {errors.form && <p className="text-red-600 text-sm">{errors.form}</p>}

        <button type="submit" disabled={submitting} className="px-4 py-2 rounded bg-black text-white disabled:opacity-50">
          {submitting ? 'Saving…' : 'Save password'}
        </button>
        <Link to="/login" onClick={handleCancel} className="text-sm text-center text-gray-600 underline">
          Cancel
        </Link>
      </form>
    </div>
  )
}
