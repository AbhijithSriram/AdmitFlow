// Client-side checks for the auth forms. These are for UX only — the backend
// (blueprints/auth.py) re-validates everything and is the source of truth.

import { textError } from './textRules'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PHONE_PATTERN = /^\d{10}$/

export const GENDERS = ['Male', 'Female', 'Other']

// The signup mobile box keeps digits only, dropping anything else as it is typed (as the name box drops
// digits). A pasted or autofilled "+91 98765 43210" or "098765 43210" loses its country/trunk prefix, so
// the 10-digit national number survives; beyond 10 digits, further typing is ignored.
export function toMobileDigits(value) {
  let digits = String(value ?? '').replace(/\D/g, '')
  if (digits.length > 10 && digits.startsWith('91')) digits = digits.slice(2)
  else if (digits.length > 10 && digits.startsWith('0')) digits = digits.slice(1)
  return digits.slice(0, 10)
}

export function validateEmail(email) {
  return EMAIL_PATTERN.test(email.trim()) ? '' : 'Enter a valid email address.'
}

export function validatePhone(phone) {
  return PHONE_PATTERN.test(phone.trim()) ? '' : 'Enter a 10-digit mobile number.'
}

// Min 8 chars, at least one number, at least one special character (FR-3).
export function validatePassword(password) {
  if (password.length < 8) return 'Password must be at least 8 characters.'
  if (!/\d/.test(password)) return 'Password must contain at least one number.'
  if (!/[^A-Za-z0-9]/.test(password)) return 'Password must contain at least one special character.'
  return ''
}

export function validateSignup(form) {
  const errors = {}
  const nameError = form.fullName.trim() ? textError('person', form.fullName, 'Full name') : 'Enter your full name.'
  if (nameError) errors.fullName = nameError
  if (!form.dateOfBirth) {
    errors.dateOfBirth = 'Enter your date of birth.'
  } else if (new Date(form.dateOfBirth) > new Date()) {
    errors.dateOfBirth = 'Date of birth cannot be in the future.'
  }
  if (!GENDERS.includes(form.gender)) errors.gender = 'Select a gender.'
  const emailError = validateEmail(form.email)
  if (emailError) errors.email = emailError
  const phoneError = validatePhone(form.phone)
  if (phoneError) errors.phone = phoneError
  return errors
}
