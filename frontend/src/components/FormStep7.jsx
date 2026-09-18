import { useEffect, useState } from 'react'
import { applicationApi, studentApi } from '../api/client'
import { usePayment } from '../hooks/usePayment'

// FR-6.9: Step 7 — Preview & Payment (read-only summary, declaration, Razorpay checkout).
//
// This component resolves its own application id via GET /api/student/dashboard instead
// of receiving it as a prop from ApplicationForm.jsx (owned by Person 2). That keeps it
// self-contained and testable on its own while Steps 1-6 are still being built — see
// IMPLEMENTATION_PLAN.md's note on stubbing cross-slice dependencies.
export default function FormStep7({ onBack }) {
  const [applicationId, setApplicationId] = useState(null)
  const [summary, setSummary] = useState({})
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [declared, setDeclared] = useState(false)

  const { status, pay } = usePayment()

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const { data: dashboard } = await studentApi.dashboard()
        const id = dashboard.data.application_id

        if (!id) {
          if (!cancelled) setLoadError('Start your application before reviewing it.')
          return
        }
        if (!cancelled) setApplicationId(id)

        const { data: draft } = await applicationApi.getDraft(id)
        if (!cancelled) setSummary(draft.data ?? {})
      } catch {
        if (!cancelled) setLoadError('Could not load your application summary.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const handlePay = async () => {
    try {
      await pay()
      // pay() only resolves after /api/app/payment/confirm has verified the Razorpay
      // signature server-side — the frontend callback alone is never trusted (SRD NFR-1).
    } catch {
      // usePayment already moved status to 'failed'; the button below re-enables.
    }
  }

  if (loading) {
    return <p>Loading your application summary…</p>
  }

  if (loadError) {
    return <p className="text-red-600">{loadError}</p>
  }

  const rows = flatten(summary)

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Preview &amp; Payment</h2>

      <div className="border rounded divide-y mb-6">
        {Object.entries(rows).map(([label, value]) => (
          <div key={label} className="flex justify-between px-3 py-2 text-sm">
            <span className="text-gray-500">{label}</span>
            <span className="font-medium">{String(value)}</span>
          </div>
        ))}
        {Object.keys(rows).length === 0 && (
          <p className="px-3 py-2 text-sm text-gray-500">No form data saved yet.</p>
        )}
      </div>

      <label className="flex items-start gap-2 text-sm mb-6">
        <input type="checkbox" checked={declared} onChange={(e) => setDeclared(e.target.checked)} />
        <span>
          I declare that the information provided in this application is true and accurate to the best of my
          knowledge.
        </span>
      </label>

      {status === 'failed' && (
        <p className="text-red-600 text-sm mb-4">Payment was not completed. You can try again below.</p>
      )}

      <div className="flex items-center justify-between mt-6">
        <button type="button" onClick={onBack} className="px-4 py-2 rounded border">
          Back
        </button>
        <button
          type="button"
          onClick={handlePay}
          disabled={!applicationId || !declared || status === 'creating' || status === 'processing'}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
        >
          {status === 'creating' || status === 'processing' ? 'Processing…' : 'Proceed to Pay'}
        </button>
      </div>
    </div>
  )
}

// Turns a possibly-nested draft object into flat "Label: value" rows for display.
// Mirrors the flattening in backend/app/services/pdf_service.py for the same reason:
// this component shouldn't need to know Person 2's exact field names to render them.
function flatten(data, prefix = '') {
  const rows = {}
  for (const [key, value] of Object.entries(data ?? {})) {
    const label = prefix ? `${prefix} / ${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(rows, flatten(value, label))
    } else {
      rows[label] = value
    }
  }
  return rows
}
