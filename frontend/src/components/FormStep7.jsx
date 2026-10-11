import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { applicationApi, studentApi } from '../api/client'
import { usePayment } from '../hooks/usePayment'
import { display, flatten, humanize } from '../utils/fieldLabels'

// FR-6.9: Step 7 — Preview & Payment (read-only summary, declaration, Razorpay checkout).
//
// This component finds its own application id via GET /api/student/dashboard rather than
// taking it as a prop, so it works wherever it is mounted. GET /api/app/draft/:id returns
// `{ draft: { "1": {...}, "2": {...} }, documents: {...}, status }` — one object per step.

const STEP_TITLES = {
  1: 'Personal Details',
  2: 'Address Details',
  3: 'Academic Details',
  4: 'Programme Preference',
  5: 'Entrance / Test Details',
  6: 'Documents',
}

const DOCUMENTS = [
  ['photo_url', 'Photo'],
  ['signature_url', 'Signature'],
  ['id_proof_url', 'ID proof'],
]

export default function FormStep7({ onBack }) {
  const navigate = useNavigate()
  const [applicationId, setApplicationId] = useState(null)
  const [steps, setSteps] = useState({})
  const [documents, setDocuments] = useState({})
  const [appStatus, setAppStatus] = useState(null)
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

        const { data: response } = await applicationApi.getDraft(id)
        if (!cancelled) {
          setSteps(response.data?.draft ?? {})
          setDocuments(response.data?.documents ?? {})
          setAppStatus(response.data?.status ?? null)
        }
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
      navigate('/dashboard')
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

  if (appStatus === 'PAID') {
    return (
      <div>
        <h2 className="text-xl font-semibold mb-2">Payment complete</h2>
        <p className="text-sm text-gray-600 mb-4">This application has been paid for and can no longer be edited.</p>
        <Link to="/dashboard" className="px-4 py-2 rounded bg-black text-white inline-block">
          Go to dashboard
        </Link>
      </div>
    )
  }

  const sections = Object.keys(steps)
    .sort((a, b) => Number(a) - Number(b))
    .map((key) => ({ title: STEP_TITLES[key] ?? `Step ${key}`, rows: flatten(steps[key]) }))
    .filter((section) => Object.keys(section.rows).length > 0)

  const busy = status === 'creating' || status === 'processing'

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Preview &amp; Payment</h2>

      {sections.length === 0 && <p className="text-sm text-gray-500 mb-4">No form data saved yet.</p>}

      {sections.map((section) => (
        <div key={section.title} className="mb-5">
          <h3 className="font-semibold mb-1">{section.title}</h3>
          <div className="border rounded divide-y">
            {Object.entries(section.rows).map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 px-3 py-2 text-sm">
                <span className="text-gray-500">{humanize(label)}</span>
                <span className="font-medium text-right">{display(value)}</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="mb-6">
        <h3 className="font-semibold mb-1">Uploaded documents</h3>
        <div className="border rounded divide-y">
          {DOCUMENTS.map(([key, label]) => (
            <div key={key} className="flex justify-between px-3 py-2 text-sm">
              <span className="text-gray-500">{label}</span>
              <span className={documents[key] ? 'font-medium text-green-700' : 'font-medium text-red-600'}>
                {documents[key] ? 'Uploaded' : 'Missing'}
              </span>
            </div>
          ))}
        </div>
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
          disabled={!applicationId || !declared || busy}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
        >
          {busy ? 'Processing…' : 'Proceed to Pay'}
        </button>
      </div>
    </div>
  )
}
