import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import Recaptcha, { RECAPTCHA_SITE_KEY } from '../components/Recaptcha'
import { GENDERS, toMobileDigits, validateSignup } from '../utils/authValidation'
import { stripFor } from '../utils/textRules'

const EMPTY_FORM = { fullName: '', dateOfBirth: '', gender: '', email: '', phone: '' }

function Field({ label, error, children }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium">
      {label}
      {children}
      {error && <span className="text-red-600 font-normal">{error}</span>}
    </label>
  )
}

const INPUT_CLASS = 'border border-gray-300 rounded px-3 py-2 font-normal'

// FR-2: student registration — name, DOB, gender, email, phone + reCAPTCHA.
export default function Signup() {
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [recaptchaToken, setRecaptchaToken] = useState('')
  const [captchaAttempt, setCaptchaAttempt] = useState(0) // bump to re-mount the widget: tokens are single-use
  const navigate = useNavigate()

  const setField = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = validateSignup(form)
    setErrors(found)
    if (RECAPTCHA_SITE_KEY && !recaptchaToken) found.recaptcha = 'Please complete the reCAPTCHA check.'
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setSubmitting(true)
    try {
      const { data } = await authApi.signup({
        full_name: form.fullName.trim(),
        date_of_birth: form.dateOfBirth,
        gender: form.gender,
        email: form.email.trim(),
        phone: form.phone.trim(),
        recaptcha_token: recaptchaToken,
      })
      const email = data.data.email
      // If this send fails the OTP page still offers a Resend button, so don't block on it.
      await authApi.sendOtp({ email, purpose: 'email_verification' }).catch(() => {})
      navigate('/verify-otp', { state: { email, purpose: 'email_verification' } })
    } catch (err) {
      const body = err.response?.data
      // The server names the offending field; map it back onto the form (snake_case -> camelCase).
      const fieldMap = { full_name: 'fullName', date_of_birth: 'dateOfBirth' }
      const field = fieldMap[body?.field] ?? body?.field ?? 'form'
      setErrors({ [field]: body?.error ?? 'Something went wrong. Please try again.' })
    } finally {
      setRecaptchaToken('')
      setCaptchaAttempt((n) => n + 1)
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} noValidate className="w-full max-w-md flex flex-col gap-4">
        <Link to="/" className="text-sm text-gray-600 underline">
          &larr; Back to home
        </Link>
        <h1 className="text-2xl font-semibold">Create your account</h1>

        <Field label="Full name" error={errors.fullName}>
          <input
            className={INPUT_CLASS}
            value={form.fullName}
            onChange={(event) => setForm((prev) => ({ ...prev, fullName: stripFor('person', event.target.value) }))}
            autoComplete="name"
          />
        </Field>

        <Field label="Date of birth" error={errors.dateOfBirth}>
          <input type="date" className={INPUT_CLASS} value={form.dateOfBirth} onChange={setField('dateOfBirth')} />
        </Field>

        <Field label="Gender" error={errors.gender}>
          <select className={INPUT_CLASS} value={form.gender} onChange={setField('gender')}>
            <option value="">Select…</option>
            {GENDERS.map((gender) => (
              <option key={gender} value={gender}>
                {gender}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Email" error={errors.email}>
          <input type="email" className={INPUT_CLASS} value={form.email} onChange={setField('email')} autoComplete="email" />
        </Field>

        <Field label="Mobile number" error={errors.phone}>
          <input
            type="tel"
            inputMode="numeric"
            className={INPUT_CLASS}
            value={form.phone}
            onChange={(event) => setForm((prev) => ({ ...prev, phone: toMobileDigits(event.target.value) }))}
            autoComplete="tel-national"
          />
        </Field>

        <div className="flex flex-col gap-1">
          <Recaptcha key={captchaAttempt} onChange={setRecaptchaToken} />
          {errors.recaptcha && <span className="text-red-600 text-sm">{errors.recaptcha}</span>}
        </div>

        {errors.form && <p className="text-red-600 text-sm">{errors.form}</p>}

        <button type="submit" disabled={submitting} className="px-4 py-2 rounded bg-black text-white disabled:opacity-50">
          {submitting ? 'Registering…' : 'Register'}
        </button>
        <p className="text-sm text-gray-600">
          Already registered?{' '}
          <Link to="/login" className="underline">
            Log in
          </Link>
        </p>
      </form>
    </div>
  )
}
