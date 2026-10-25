import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { applicationApi, studentApi } from '../api/client'
import AppHeader from '../components/AppHeader'
import StatusBadge from '../components/StatusBadge'
import TestsCard from '../components/TestsCard'
import { usePayment } from '../hooks/usePayment'

// FR-5: applicant dashboard — status badge, quick actions, navigation links.
export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [receiptError, setReceiptError] = useState(null)
  const [retryMessage, setRetryMessage] = useState(null)
  const { status: paymentStatus, pay } = usePayment()

  const loadDashboard = useCallback(() => {
    return studentApi
      .dashboard()
      .then((response) => setData(response.data.data))
      .catch(() => setLoadError('Could not load your dashboard. Try refreshing.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  // FR-6.9: after a failed or abandoned payment the dashboard offers "Retry Payment", which opens the
  // Razorpay checkout again straight from here (a fresh order is created; the old attempt stays FAILED).
  const handleRetryPayment = async () => {
    setRetryMessage(null)
    try {
      await pay() // resolves only after the server has verified the signature
      setRetryMessage({ ok: true, text: 'Payment received. Your confirmation email is on its way.' })
    } catch {
      setRetryMessage({ ok: false, text: 'The payment was not completed. You can try again.' })
    }
    await loadDashboard()
  }

  const handleViewReceipt = async () => {
    setReceiptError(null)
    try {
      const { data: receipt } = await applicationApi.getReceipt(data.application_id)
      window.open(receipt.data.url, '_blank', 'noopener')
    } catch {
      setReceiptError('Could not load your receipt. Try again in a moment.')
    }
  }

  if (loading) {
    return <p className="p-6">Loading your dashboard…</p>
  }

  if (loadError) {
    return <p className="p-6 text-red-600">{loadError}</p>
  }

  const status = data?.status ?? 'NOT_STARTED'
  const paymentBusy = paymentStatus === 'creating' || paymentStatus === 'processing'

  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold mb-2">Welcome{data?.full_name ? `, ${data.full_name}` : ''}</h1>
        <StatusBadge status={status} />

        {data?.programme && (
          <p className="text-gray-600 mt-2">
            {data.programme}
            {data.specialisation ? ` — ${data.specialisation}` : ''}
          </p>
        )}

        <div className="flex flex-wrap gap-3 mt-6">
          {status === 'PAYMENT_PENDING' && (
            <button
              type="button"
              onClick={handleRetryPayment}
              disabled={paymentBusy}
              className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
            >
              {paymentBusy ? 'Processing…' : 'Retry Payment'}
            </button>
          )}
          {status !== 'PAID' && (
            <Link
              to="/application"
              className={`px-4 py-2 rounded ${status === 'PAYMENT_PENDING' ? 'border' : 'bg-black text-white'}`}
            >
              {status === 'NOT_STARTED' ? 'Start Application' : 'Continue Application'}
            </Link>
          )}
          {data?.has_receipt && (
            <button type="button" onClick={handleViewReceipt} className="px-4 py-2 rounded border">
              View Receipt
            </button>
          )}
          <a href="/brochure.pdf" target="_blank" rel="noopener noreferrer" className="px-4 py-2 rounded border">
            Download Brochure
          </a>
        </div>

        {receiptError && <p className="text-red-600 text-sm mt-2">{receiptError}</p>}
        {retryMessage && (
          <p className={`text-sm mt-2 ${retryMessage.ok ? 'text-green-700' : 'text-red-600'}`} role="status">
            {retryMessage.text}
          </p>
        )}

        {/* Assigned aptitude tests (FR-10). Renders nothing until Person 1 builds it. */}
        {status === 'PAID' && <TestsCard />}

        <nav className="flex flex-wrap gap-4 mt-8 text-sm text-gray-600">
          <Link to="/info/eligibility" className="underline">
            Eligibility &amp; Fee Structure
          </Link>
          <Link to="/info/dates" className="underline">
            Important Dates
          </Link>
          <Link to="/info/guidelines" className="underline">
            Guidelines
          </Link>
          <Link to="/info/contact" className="underline">
            Contact
          </Link>
        </nav>
      </div>
    </div>
  )
}
