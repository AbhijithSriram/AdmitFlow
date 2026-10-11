import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { adminApi } from '../../api/client'
import StatusBadge from '../../components/StatusBadge'
import DeleteStudentModal from './DeleteStudentModal'
import StudentDetailPanel from './StudentDetailPanel'
import { PAYMENT_LABELS, STAGE_OPTIONS, errorMessage, formatDate } from './adminUtils'
import { useAdminSession } from './useAdminSession'

// FR-7.2: paginated, sortable, searchable, filterable table of all applicants.
const COLUMNS = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'email', label: 'Email', sortable: true },
  { key: 'phone', label: 'Phone' },
  { key: 'registered_at', label: 'Registered', sortable: true },
  { key: 'stage', label: 'Stage', sortable: true },
  { key: 'payment_status', label: 'Payment' },
]

const PAYMENT_STYLE = {
  NONE: 'bg-gray-200 text-gray-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-green-100 text-green-800',
}

const field = 'border border-slate-400 rounded-md px-3 py-2 text-sm bg-white focus:outline-2 focus:outline-indigo-600'

export default function AdminDashboard() {
  const { status, admin, signOut, expire } = useAdminSession()
  const [query, setQuery] = useState({ page: 1, sort: 'registered_at', order: 'desc', q: '', stage: '', payment_status: '' })
  const [search, setSearch] = useState('')
  const [loaded, setLoaded] = useState({ key: null, data: { students: [], total: 0, total_pages: 1 } })
  const [reloadCount, setReloadCount] = useState(0)
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState(null)
  const [toDelete, setToDelete] = useState(null)

  // Search is debounced (500 ms) so we don't query on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setQuery((q) => (q.q === search ? q : { ...q, q: search, page: 1 })), 500)
    return () => clearTimeout(t)
  }, [search])

  // "loading" is derived: the table is loading until the response for the CURRENT query arrives.
  const requestKey = JSON.stringify([query, reloadCount])
  const loading = loaded.key !== requestKey
  const data = loaded.data
  const reload = () => setReloadCount((n) => n + 1)

  useEffect(() => {
    if (status !== 'authed') return undefined
    let cancelled = false
    adminApi
      .listStudents(query)
      .then((res) => {
        if (cancelled) return
        setError('')
        setLoaded({ key: requestKey, data: res.data.data })
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) expire()
        else {
          setError(errorMessage(err))
          setLoaded((l) => ({ ...l, key: requestKey }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [status, query, requestKey, expire])

  if (status === 'loading') return <p className="p-10 text-center text-slate-600">Checking your session…</p>
  if (status === 'anon') return <Navigate to="/admin/auth" replace />

  const setFilter = (patch) => setQuery((q) => ({ ...q, ...patch, page: 1 }))
  const sortBy = (key) => setFilter({ sort: key, order: query.sort === key && query.order === 'asc' ? 'desc' : 'asc' })

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center gap-4 bg-slate-900 text-white px-6 py-3">
        <strong>AdmitFlow staff</strong>
        <span className="ml-auto text-slate-300 text-sm">{admin?.name}</span>
        <button onClick={signOut} className="text-sm border border-slate-500 rounded-md px-3 py-1 hover:bg-slate-700">
          Sign out
        </button>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-semibold text-slate-900 mb-4">Applicants</h1>

        <div className="grid gap-4 md:grid-cols-[2fr_1fr_1fr] mb-4">
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
            Search
            <input type="search" placeholder="Name, email or phone" value={search} onChange={(e) => setSearch(e.target.value)} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
            Stage
            <select value={query.stage} onChange={(e) => setFilter({ stage: e.target.value })} className={field}>
              <option value="">All stages</option>
              {STAGE_OPTIONS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
            Payment
            <select value={query.payment_status} onChange={(e) => setFilter({ payment_status: e.target.value })} className={field}>
              <option value="">All payments</option>
              {Object.entries(PAYMENT_LABELS).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <p role="alert" className="text-sm font-medium text-red-700 mb-3">
            {error}{' '}
            <button onClick={reload} className="underline">
              Try again
            </button>
          </p>
        )}

        <div className={`overflow-x-auto bg-white border border-slate-200 rounded-lg ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
          <table className="w-full min-w-[820px] text-sm text-left">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.key} className="px-3 py-2 font-semibold" aria-sort={query.sort === c.key ? (query.order === 'asc' ? 'ascending' : 'descending') : undefined}>
                    {c.sortable ? (
                      <button onClick={() => sortBy(c.key)} className="font-semibold hover:underline">
                        {c.label}
                        {query.sort === c.key ? (query.order === 'asc' ? ' ▲' : ' ▼') : ''}
                      </button>
                    ) : (
                      c.label
                    )}
                  </th>
                ))}
                <th className="px-3 py-2">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.students.map((s) => (
                <tr key={s.id} className="border-t border-slate-200 hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <button onClick={() => setOpenId(s.id)} className="text-indigo-700 font-medium hover:underline text-left">
                      {s.name}
                    </button>
                  </td>
                  <td className="px-3 py-2">{s.email}</td>
                  <td className="px-3 py-2">{s.phone}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{formatDate(s.registered_at)}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={s.stage} />
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${PAYMENT_STYLE[s.payment_status]}`}>{PAYMENT_LABELS[s.payment_status]}</span>
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button onClick={() => setOpenId(s.id)} className="text-sm border border-slate-400 rounded-md px-2 py-1 mr-2 hover:bg-slate-100">
                      View
                    </button>
                    <button onClick={() => setToDelete(s)} className="text-sm border border-red-300 text-red-700 rounded-md px-2 py-1 hover:bg-red-50">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && data.students.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-slate-600">
                    {query.q || query.stage || query.payment_status
                      ? 'No applicants match these filters. Clear a filter or change the search.'
                      : 'No applicants have registered yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <nav aria-label="Pagination" className="flex items-center gap-3 justify-end mt-4 text-sm">
          <span className="mr-auto text-slate-600">
            {data.total} applicant{data.total === 1 ? '' : 's'}
          </span>
          <button disabled={query.page <= 1} onClick={() => setQuery({ ...query, page: query.page - 1 })} className="border border-slate-400 rounded-md px-3 py-1 bg-white disabled:opacity-50">
            Previous
          </button>
          <span>
            Page {data.page ?? query.page} of {data.total_pages}
          </span>
          <button disabled={query.page >= data.total_pages} onClick={() => setQuery({ ...query, page: query.page + 1 })} className="border border-slate-400 rounded-md px-3 py-1 bg-white disabled:opacity-50">
            Next
          </button>
        </nav>
      </main>

      {openId && <StudentDetailPanel key={openId} studentId={openId} onClose={() => setOpenId(null)} onDelete={setToDelete} onUnauthorised={expire} />}
      {toDelete && (
        <DeleteStudentModal
          student={toDelete}
          onClose={() => setToDelete(null)}
          onDeleted={() => {
            setToDelete(null)
            setOpenId(null)
            reload()
          }}
        />
      )}
    </div>
  )
}
