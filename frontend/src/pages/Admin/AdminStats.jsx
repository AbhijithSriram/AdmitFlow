import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { adminStatsApi } from '../../api/client'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
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

const WHOLE_NUMBER = /^\d+$/
const shortDate = (iso) => {
  const [, month, day] = String(iso).split('-')
  return month && day ? `${day}/${month}` : String(iso)
}
const seatKey = (r) => `${r.programme}||${r.specialisation}`

export default function AdminStats() {
  const { status, admin, signOut, expire } = useAdminSession()
  const [loaded, setLoaded] = useState({ key: null, summary: null, programmes: [] })
  const [reloadCount, setReloadCount] = useState(0)
  const [error, setError] = useState('')
  const [seatRows, setSeatRows] = useState([])
  const [edits, setEdits] = useState({})
  const [saving, setSaving] = useState(false)
  const [seatError, setSeatError] = useState('')
  const [seatNotice, setSeatNotice] = useState('')
  const [rangeInput, setRangeInput] = useState({ from: '', to: '' })
  const [range, setRange] = useState({ from: '', to: '' })
  const [chartReload, setChartReload] = useState(0)
  const [chart, setChart] = useState({ key: null, data: [], from: '', to: '' })
  const [chartError, setChartError] = useState('')
  const chartKey = `${range.from}|${range.to}|${chartReload}`
  const chartLoading = chart.key !== chartKey

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

  useEffect(() => {
    if (status !== 'authed') return undefined
    let cancelled = false
    adminStatsApi
      .getSeats()
      .then((res) => {
        if (!cancelled) setSeatRows(res.data.data.seats)
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) expire()
        else setSeatError(errorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [status, expire])

  const rowsView = seatRows.map((r) => {
    const key = seatKey(r)
    const text = edits[key] ?? String(r.seats)
    const valid = WHOLE_NUMBER.test(text)
    return { ...r, key, text, valid, changed: valid && Number(text) !== r.seats }
  })
  const changedRows = rowsView.filter((r) => r.changed)
  const hasInvalid = rowsView.some((r) => !r.valid)

  const handleSave = async () => {
    setSaving(true)
    setSeatError('')
    setSeatNotice('')
    try {
      const body = changedRows.map((r) => ({ programme: r.programme, specialisation: r.specialisation, seats: Number(r.text) }))
      const res = await adminStatsApi.setSeats(body)
      setSeatRows(res.data.data.seats)
      setEdits({})
      const n = res.data.data.changed
      setSeatNotice(n === 0 ? 'No changes to save.' : `Saved ${n} change${n === 1 ? '' : 's'}.`)
      reload()
    } catch (err) {
      if (err?.response?.status === 401) expire()
      else setSeatError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    if (status !== 'authed') return undefined
    let cancelled = false
    const params = {}
    if (range.from && range.to) {
      params.from = range.from
      params.to = range.to
    }
    adminStatsApi
      .registrations(params)
      .then((res) => {
        if (cancelled) return
        const d = res.data.data
        setChartError('')
        setChart({ key: chartKey, data: d.registrations, from: d.from, to: d.to })
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) expire()
        else {
          setChartError(errorMessage(err))
          setChart((c) => ({ ...c, key: chartKey }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [status, range, chartKey, expire])

  const chartTotal = chart.data.reduce((sum, d) => sum + d.count, 0)
  const rangeOk = Boolean(rangeInput.from && rangeInput.to && rangeInput.from <= rangeInput.to)
  const rangeBackwards = Boolean(rangeInput.from && rangeInput.to && rangeInput.from > rangeInput.to)
  const applyRange = () => setRange({ from: rangeInput.from, to: rangeInput.to })
  const clearRange = () => {
    setRangeInput({ from: '', to: '' })
    setRange({ from: '', to: '' })
  }

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

        <section aria-labelledby="registrations-heading" className="mt-8 bg-white border border-slate-200 rounded-lg p-4">
          <h2 id="registrations-heading" className="text-lg font-semibold text-slate-900 mb-1">
            Registrations per day
          </h2>
          <p className="text-sm text-slate-600 mb-3">
            {chart.from && chart.to ? `${chart.from} to ${chart.to}` : 'Last 30 days'}
          </p>
          <div className="flex flex-wrap items-end gap-3 mb-1">
            <label className="text-sm text-slate-700">
              From
              <input
                type="date"
                value={rangeInput.from}
                onChange={(e) => setRangeInput((r) => ({ ...r, from: e.target.value }))}
                className="block mt-1 rounded-md border border-slate-300 px-2 py-1"
              />
            </label>
            <label className="text-sm text-slate-700">
              To
              <input
                type="date"
                value={rangeInput.to}
                onChange={(e) => setRangeInput((r) => ({ ...r, to: e.target.value }))}
                className="block mt-1 rounded-md border border-slate-300 px-2 py-1"
              />
            </label>
            <button
              onClick={applyRange}
              disabled={!rangeOk}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Apply
            </button>
            <button
              onClick={clearRange}
              disabled={!range.from && !range.to && !rangeInput.from && !rangeInput.to}
              className="px-3 py-1.5 border border-slate-300 rounded-md text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Last 30 days
            </button>
          </div>
          <p className={`text-xs mb-3 ${rangeBackwards ? 'text-red-700 font-medium' : 'text-slate-500'}`}>
            {rangeBackwards ? 'The start date must not be after the end date.' : 'Pick both dates, or use Last 30 days.'}
          </p>
          {chartError && (
            <p role="alert" className="text-sm font-medium text-red-700 mb-3">
              {chartError}{' '}
              <button onClick={() => setChartReload((n) => n + 1)} className="underline">
                Try again
              </button>
            </p>
          )}
          <div className={chartLoading ? 'opacity-60' : ''} aria-busy={chartLoading}>
            {chartLoading && chart.data.length === 0 && <p className="text-sm text-slate-600">Loading chart…</p>}
            {!chartLoading && !chartError && chartTotal === 0 && (
              <p className="text-sm text-slate-600 py-6 text-center">No registrations in this period.</p>
            )}
            {chart.data.length > 0 && chartTotal > 0 && (
              <div
                role="img"
                aria-label={`Bar chart of registrations per day, ${chart.from} to ${chart.to}, ${chartTotal} in total`}
                className="h-64"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart.data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={shortDate} interval="preserveStartEnd" minTickGap={16} />
                    <YAxis allowDecimals={false} width={32} />
                    <Tooltip formatter={(value) => [value, 'Registrations']} />
                    <Bar dataKey="count" fill="#2563eb" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </section>

        <section aria-labelledby="seat-editor-heading" className="mt-8 bg-white border border-slate-200 rounded-lg p-4">
          <h2 id="seat-editor-heading" className="text-lg font-semibold text-slate-900 mb-1">
            Edit seat numbers
          </h2>
          <p className="text-sm text-slate-600 mb-3">Change a number and press Save. Only the rows you changed are sent.</p>
          {seatError && (
            <p role="alert" className="text-sm font-medium text-red-700 mb-3">
              {seatError}
            </p>
          )}
          {seatNotice && (
            <p role="status" className="text-sm font-medium text-green-700 mb-3">
              {seatNotice}
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {rowsView.map((r, i) => (
              <div key={r.key} className="flex items-center gap-3">
                <label htmlFor={`seats-${i}`} className="flex-1 text-sm text-slate-800">
                  {r.programme} – {r.specialisation}
                </label>
                <input
                  id={`seats-${i}`}
                  type="number"
                  min="0"
                  step="1"
                  inputMode="numeric"
                  value={r.text}
                  aria-invalid={!r.valid}
                  onChange={(e) => {
                    setSeatNotice('')
                    setEdits((prev) => ({ ...prev, [r.key]: e.target.value }))
                  }}
                  className={`w-24 rounded-md border px-2 py-1 text-right tabular-nums ${r.valid ? 'border-slate-300' : 'border-red-500'}`}
                />
              </div>
            ))}
          </div>
          {hasInvalid && (
            <p role="alert" className="text-sm font-medium text-red-700 mt-3">
              Seat numbers must be whole numbers, 0 or more.
            </p>
          )}
          {seatRows.length > 0 && (
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleSave}
                disabled={saving || hasInvalid || changedRows.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving…' : 'Save seat numbers'}
              </button>
              <button
                onClick={() => setEdits({})}
                disabled={saving || Object.keys(edits).length === 0}
                className="px-4 py-2 border border-slate-300 rounded-md text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Reset
              </button>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
