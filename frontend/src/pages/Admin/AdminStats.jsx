import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { adminStatsApi } from '../../api/client'
import { errorMessage } from './adminUtils'
import { useAdminSession } from './useAdminSession'

// SRD FR-11: the ERP statistics view (summary cards, programme table, registrations chart). Owner: Person 2.
const CARDS = [
  { key: 'registrations', label: 'Registrations' },
  { key: 'applications_started', label: 'Applications started' },
  { key: 'paid', label: 'Paid' },
  { key: 'payment_pending', label: 'Payment pending' },
]

const NUMBER_COLUMNS = [
  { key: 'seats', label: 'Seats' },
  { key: 'applied', label: 'Applied' },
  { key: 'paid', label: 'Paid' },
  { key: 'shortlisted', label: 'Shortlisted' },
]

export default function AdminStats() {
  const { status, admin, signOut, expire } = useAdminSession()
  const [loaded, setLoaded] = useState({ key: null, summary: null, programmes: [] })
  const [reloadCount, setReloadCount] = useState(0)
  const [error, setError] = useState('')

  // "loading" is derived: the numbers are loading until the response for the CURRENT request arrives.
  const loading = loaded.key !== reloadCount
  const reload = () => setReloadCount((n) => n + 1)

  useEffect(() => {
    if (status !== 'authed') return undefined
    let cancelled = false
    Promise.all([adminStatsApi.summary(), adminStatsApi.programmes()])
      .then(([summaryRes, programmesRes]) => {
        if (cancelled) return
        setError('')
        setLoaded({ key: reloadCount, summary: summaryRes.data.data, programmes: programmesRes.data.data.programmes })
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) expire()
        else {
          setError(errorMessage(err))
          setLoaded((l) => ({ ...l, key: reloadCount }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [status, reloadCount, expire])

  if (status === 'loading') return <p className="p-10 text-center text-slate-600">Checking your session…</p>
  if (status === 'anon') return <Navigate to="/admin/auth" replace />

  const { summary, programmes } = loaded
  const totals = NUMBER_COLUMNS.reduce((acc, c) => ({ ...acc, [c.key]: programmes.reduce((sum, p) => sum + p[c.key], 0) }), {})

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center gap-4 bg-slate-900 text-white px-6 py-3">
        <strong>AdmitFlow staff</strong>
        <Link to="/admin/dashboard" className="text-sm text-slate-300 underline hover:text-white">
          Applicants
        </Link>
        <span className="ml-auto text-slate-300 text-sm">{admin?.name}</span>
        <button onClick={signOut} className="text-sm border border-slate-500 rounded-md px-3 py-1 hover:bg-slate-700">
          Sign out
        </button>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-semibold text-slate-900 mb-4">Statistics</h1>

        {error && (
          <p role="alert" className="text-sm font-medium text-red-700 mb-3">
            {error}{' '}
            <button onClick={reload} className="underline">
              Try again
            </button>
          </p>
        )}

        <section aria-label="Summary" className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6 ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
          {CARDS.map((c) => (
            <div key={c.key} className="bg-white border border-slate-200 rounded-lg p-4">
              <p className="text-sm text-slate-600">{c.label}</p>
              <p className="text-3xl font-semibold text-slate-900 mt-1">{summary ? summary[c.key] : '–'}</p>
            </div>
          ))}
        </section>

        <h2 className="text-lg font-semibold text-slate-900 mb-2">Seats and applicants by programme</h2>
        <div className={`overflow-x-auto bg-white border border-slate-200 rounded-lg ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
          <table className="w-full min-w-[640px] text-sm text-left">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 font-semibold">Programme</th>
                <th className="px-3 py-2 font-semibold">Specialisation</th>
                {NUMBER_COLUMNS.map((c) => (
                  <th key={c.key} className="px-3 py-2 font-semibold text-right">
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {programmes.map((p) => (
                <tr key={`${p.programme}/${p.specialisation}`}>
                  <td className="px-3 py-2">{p.programme}</td>
                  <td className="px-3 py-2">{p.specialisation}</td>
                  {NUMBER_COLUMNS.map((c) => (
                    <td key={c.key} className="px-3 py-2 text-right tabular-nums">
                      {p[c.key]}
                    </td>
                  ))}
                </tr>
              ))}
              {!loading && programmes.length === 0 && (
                <tr>
                  <td colSpan={2 + NUMBER_COLUMNS.length} className="px-3 py-6 text-center text-slate-600">
                    No programmes yet.
                  </td>
                </tr>
              )}
            </tbody>
            {programmes.length > 0 && (
              <tfoot className="bg-slate-50 font-semibold text-slate-900">
                <tr>
                  <td className="px-3 py-2" colSpan={2}>
                    Total
                  </td>
                  {NUMBER_COLUMNS.map((c) => (
                    <td key={c.key} className="px-3 py-2 text-right tabular-nums">
                      {totals[c.key]}
                    </td>
                  ))}
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </main>
    </div>
  )
}
