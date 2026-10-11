import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import { GENDERS, validateSignup } from '../utils/authValidation'

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
  const navigate = useNavigate()

  const setField = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = validateSignup(form)
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
      })
      navigate('/verify-otp', { state: { email: data.data.email } })
    } catch (err) {
      const body = err.response?.data
      // The server names the offending field; map it back onto the form (snake_case -> camelCase).
      const fieldMap = { full_name: 'fullName', date_of_birth: 'dateOfBirth' }
      const field = fieldMap[body?.field] ?? body?.field ?? 'form'
      setErrors({ [field]: body?.error ?? 'Something went wrong. Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} noValidate className="w-full max-w-md flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">Create your account</h1>

        <Field label="Full name" error={errors.fullName}>
          <input className={INPUT_CLASS} value={form.fullName} onChange={setField('fullName')} autoComplete="name" />
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
            maxLength={10}
            className={INPUT_CLASS}
            value={form.phone}
            onChange={setField('phone')}
            autoComplete="tel-national"
          />
        </Field>

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
