import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { applicationApi, studentApi } from '../api/client'
import StatusBadge from '../components/StatusBadge'

// FR-5: applicant dashboard — status badge, quick actions, navigation links.
export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [receiptError, setReceiptError] = useState(null)

  useEffect(() => {
    let cancelled = false

    studentApi
      .dashboard()
      .then((response) => {
        if (!cancelled) setData(response.data.data)
      })
      .catch(() => {
        if (!cancelled) setLoadError('Could not load your dashboard. Try refreshing.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

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

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-2">Welcome{data?.full_name ? `, ${data.full_name}` : ''}</h1>
      <StatusBadge status={status} />

      {data?.programme && (
        <p className="text-gray-600 mt-2">
          {data.programme}
          {data.specialisation ? ` — ${data.specialisation}` : ''}
        </p>
      )}

      <div className="flex flex-wrap gap-3 mt-6">
        {status !== 'PAID' && (
          <Link to="/application" className="px-4 py-2 rounded bg-black text-white">
            {status === 'NOT_STARTED' ? 'Start Application' : 'Continue Application'}
          </Link>
        )}
        {data?.has_receipt && (
          <button type="button" onClick={handleViewReceipt} className="px-4 py-2 rounded border">
            View Receipt
          </button>
        )}
        {/* TODO: point at the real brochure asset once the institution supplies one */}
        <a href="/brochure.pdf" target="_blank" rel="noopener noreferrer" className="px-4 py-2 rounded border">
          Download Brochure
        </a>
      </div>

      {receiptError && <p className="text-red-600 text-sm mt-2">{receiptError}</p>}

      <nav className="flex flex-wrap gap-4 mt-8 text-sm text-gray-600">
        <a href="#eligibility">Eligibility &amp; Fee Structure</a>
        <a href="#dates">Important Dates</a>
        <a href="#guidelines">Guidelines</a>
        <a href="#contact">Contact</a>
      </nav>
    </div>
  )
}
