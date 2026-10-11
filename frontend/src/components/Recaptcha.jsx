import { useEffect, useRef } from 'react'

const SCRIPT_SRC = 'https://www.google.com/recaptcha/api.js?render=explicit'
export const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY

let scriptPromise = null
function loadRecaptchaScript() {
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = SCRIPT_SRC
      script.async = true
      script.onload = () => window.grecaptcha.ready(() => resolve(window.grecaptcha))
      script.onerror = () => {
        scriptPromise = null
        reject(new Error('Could not load reCAPTCHA'))
      }
      document.head.appendChild(script)
    })
  }
  return scriptPromise
}

// reCAPTCHA v2 checkbox. Calls onChange(token) on success and onChange('') on expiry.
// Renders nothing when no site key is configured (local dev; the backend skips the check in debug).
export default function Recaptcha({ onChange }) {
  const containerRef = useRef(null)
  const onChangeRef = useRef(onChange)

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    if (!RECAPTCHA_SITE_KEY) return undefined
    let cancelled = false
    loadRecaptchaScript()
      .then((grecaptcha) => {
        if (cancelled || !containerRef.current) return
        grecaptcha.render(containerRef.current, {
          sitekey: RECAPTCHA_SITE_KEY,
          callback: (token) => onChangeRef.current(token),
          'expired-callback': () => onChangeRef.current(''),
          'error-callback': () => onChangeRef.current(''),
        })
      })
      .catch(() => onChangeRef.current(''))
    return () => {
      cancelled = true
    }
  }, [])

  if (!RECAPTCHA_SITE_KEY) return null
  return <div ref={containerRef} />
}
