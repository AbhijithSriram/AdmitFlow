import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { adminTestsApi } from '../../api/client'
import { errorMessage, formatDateTime } from './adminUtils'
import { useAdminSession } from './useAdminSession'

// SRD FR-10: admin list of aptitude tests, with publish, assign, results and delete.
const field = 'border border-slate-400 rounded-md px-3 py-2 text-sm bg-white focus:outline-2 focus:outline-indigo-600'
const btn = 'text-sm border border-slate-400 rounded-md px-2 py-1 hover:bg-slate-100 disabled:opacity-50'
const STATUS = { ASSIGNED: 'Not started', IN_PROGRESS: 'In progress', SUBMITTED: 'Submitted' }

function Overlay({ title, onClose, children, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div role="dialog" aria-modal="true" aria-label={title} className={`bg-white rounded-lg w-full p-6 max-h-[90vh] overflow-y-auto ${wide ? 'max-w-4xl' : 'max-w-md'}`}>
        <div className="flex items-start justify-between gap-4 mb-3">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="text-sm underline">Close</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function AssignDialog({ paper, onClose, onExpired, onDone }) {
  const [programme, setProgramme] = useState('')
  const [specialisation, setSpecialisation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function assign() {
    setBusy(true)
    setError('')
    const filters = {}
    if (programme.trim()) filters.programme = programme.trim()
    if (specialisation.trim()) filters.specialisation = specialisation.trim()
    try {
      setResult((await adminTestsApi.assign(paper.id, filters)).data.data)
    } catch (err) {
      if (err?.response?.status === 401) onExpired()
      else setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Overlay title={`Assign “${paper.title}”`} onClose={result ? onDone : onClose}>
      {!result ? (
        <>
          <p className="text-sm text-slate-700">
            This gives the test to every applicant who has <strong>paid</strong>. Leave both boxes empty for everyone, or narrow it down.
            Assigning again is safe: nobody gets it twice and nobody’s progress is reset.
          </p>
          <label className="block text-sm font-medium text-slate-800 mt-4">
            Programme (optional)
            <input className={`${field} w-full mt-1 font-normal`} value={programme} onChange={(e) => setProgramme(e.target.value)} />
          </label>
          <label className="block text-sm font-medium text-slate-800 mt-3">
            Specialisation (optional)
            <input className={`${field} w-full mt-1 font-normal`} value={specialisation} onChange={(e) => setSpecialisation(e.target.value)} />
          </label>
          {error && <p role="alert" className="text-sm font-medium text-red-700 mt-3">{error}</p>}
          <div className="flex justify-end gap-2 mt-5">
            <button onClick={onClose} disabled={busy} className={btn}>Cancel</button>
            <button onClick={assign} disabled={busy} className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700 disabled:opacity-50">
              {busy ? 'Assigning…' : 'Assign test'}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-sm text-slate-800">
            Assigned to <strong>{result.assigned}</strong> applicant{result.assigned === 1 ? '' : 's'}.
            {result.already_assigned > 0 && ` ${result.already_assigned} already had it.`}
            {result.eligible === 0 && ' No paid applicants matched.'}
          </p>
          <div className="flex justify-end mt-5">
            <button onClick={onDone} className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700">Done</button>
          </div>
        </>
      )}
    </Overlay>
  )
}

function ResultsDialog({ paper, onClose, onExpired }) {
  const [page, setPage] = useState(1)
  const [reload, setReload] = useState(0)
  const [loaded, setLoaded] = useState({ key: null, data: null })
  const [error, setError] = useState('')
  const key = `${page}:${reload}`
  const loading = loaded.key !== key
  const data = loaded.data

  useEffect(() => {
    let cancelled = false
    adminTestsApi
      .results(paper.id, { page })
      .then((res) => {
        if (cancelled) return
        setError('')
        setLoaded({ key, data: res.data.data })
      })
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) {
          onExpired()
        } else {
          setError(errorMessage(err))
          setLoaded((l) => ({ ...l, key }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [paper.id, page, key, onExpired])

  async function reset(row) {
    if (!window.confirm(`Let ${row.name} take “${paper.title}” again? Their answers and score will be cleared.`)) return
    try {
      await adminTestsApi.resetAttempt(paper.id, row.application_id)
      setReload((n) => n + 1)
    } catch (err) {
      if (err?.response?.status === 401) onExpired()
      else setError(errorMessage(err))
    }
  }

  return (
    <Overlay title={`Results: ${paper.title}`} onClose={onClose} wide>
      {error && <p role="alert" className="text-sm font-medium text-red-700 mb-2">{error}</p>}
      {data && (
        <p className="text-sm text-slate-700 mb-3">
          {data.summary.assigned} assigned · {data.summary.started} started · {data.summary.submitted} submitted ·{' '}
          {data.summary.passed} passed (pass mark {data.paper.pass_marks} of {data.paper.total_marks})
        </p>
      )}
      <div className={`overflow-x-auto border border-slate-200 rounded-lg ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
        <table className="w-full min-w-[700px] text-sm text-left">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              {['Applicant', 'Programme', 'Status', 'Score', 'Result', 'Submitted', ''].map((h) => (
                <th key={h} className="px-3 py-2 font-semibold">{h || <span className="sr-only">Actions</span>}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.results.map((r) => (
              <tr key={r.application_id} className="border-t border-slate-200">
                <td className="px-3 py-2">{r.name}<div className="text-xs text-slate-500">{r.email}</div></td>
                <td className="px-3 py-2">{[r.programme, r.specialisation].filter(Boolean).join(' · ') || '—'}</td>
                <td className="px-3 py-2">{STATUS[r.status]}</td>
                <td className="px-3 py-2">{r.score ?? '—'}</td>
                <td className="px-3 py-2">{r.passed === null ? '—' : r.passed ? 'Passed' : 'Not passed'}</td>
                <td className="px-3 py-2 whitespace-nowrap">{r.submitted_at ? formatDateTime(r.submitted_at) : '—'}</td>
                <td className="px-3 py-2 text-right">
                  {r.status !== 'ASSIGNED' && <button onClick={() => reset(r)} className={btn}>Reset attempt</button>}
                </td>
              </tr>
            ))}
            {data && data.results.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-600">Nobody has been assigned this test yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {data && (
        <nav aria-label="Pagination" className="flex items-center gap-3 justify-end mt-3 text-sm">
          <span className="mr-auto text-slate-600">{data.total} applicant{data.total === 1 ? '' : 's'}</span>
          <button className={btn} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {data.page} of {data.total_pages}</span>
          <button className={btn} disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</button>
        </nav>
      )}
    </Overlay>
  )
}

export default function AdminTests() {
  const { status, expire } = useAdminSession()
  const [reload, setReload] = useState(0)
  const [loaded, setLoaded] = useState({ key: null, tests: [] })
  const [notice, setNotice] = useState(null) // {kind: 'ok' | 'error', text}
  const [assigning, setAssigning] = useState(null)
  const [viewing, setViewing] = useState(null)
  const loading = loaded.key !== reload

  useEffect(() => {
    if (status !== 'authed') return undefined
    let cancelled = false
    adminTestsApi
      .list()
      .then((res) => !cancelled && setLoaded({ key: reload, tests: res.data.data.tests }))
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) {
          expire()
        } else {
          setNotice({ kind: 'error', text: errorMessage(err) })
          setLoaded((l) => ({ ...l, key: reload }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [status, reload, expire])

  if (status === 'loading') return <p className="p-10 text-center text-slate-600">Checking your session…</p>
  if (status === 'anon') return <Navigate to="/admin/auth" replace />

  async function act(fn, successText) {
    setNotice(null)
    try {
      await fn()
      setNotice({ kind: 'ok', text: successText })
      setReload((n) => n + 1)
    } catch (err) {
      if (err?.response?.status === 401) expire()
      else setNotice({ kind: 'error', text: errorMessage(err) })
    }
  }

  const publish = (t) => act(() => adminTestsApi.publish(t.id), `“${t.title}” is published. You can now assign it.`)
  const remove = (t) =>
    window.confirm(`Delete “${t.title}” and its questions? This cannot be undone.`) &&
    act(() => adminTestsApi.remove(t.id), `“${t.title}” was deleted.`)

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center gap-4 bg-slate-900 text-white px-6 py-3">
        <strong>AdmitFlow staff</strong>
        <nav aria-label="Admin sections" className="flex gap-4 text-sm ml-4">
          <Link to="/admin/dashboard" className="hover:underline">Applicants</Link>
          <Link to="/admin/stats" className="hover:underline">Statistics</Link>
          <Link to="/admin/tests" className="underline">Tests</Link>
        </nav>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-semibold text-slate-900">Aptitude tests</h1>
          <Link to="/admin/tests/new" className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700">New test</Link>
        </div>

        {notice && (
          <p role={notice.kind === 'error' ? 'alert' : 'status'} className={`text-sm font-medium mb-3 ${notice.kind === 'error' ? 'text-red-700' : 'text-green-800'}`}>
            {notice.text}
          </p>
        )}

        <div className={`overflow-x-auto bg-white border border-slate-200 rounded-lg ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
          <table className="w-full min-w-[860px] text-sm text-left">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                {['Title', 'Time', 'Marks (pass)', 'Questions', 'Status', 'Assigned', 'Submitted', ''].map((h) => (
                  <th key={h} className="px-3 py-2 font-semibold">{h || <span className="sr-only">Actions</span>}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loaded.tests.map((t) => (
                <tr key={t.id} className="border-t border-slate-200">
                  <td className="px-3 py-2 font-medium">{t.title}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{t.duration_minutes} min</td>
                  <td className="px-3 py-2 whitespace-nowrap">{t.total_marks} ({t.pass_marks})</td>
                  <td className="px-3 py-2">{t.question_count}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${t.is_published ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-800'}`}>
                      {t.is_published ? 'Published' : 'Draft'}
                    </span>
                  </td>
                  <td className="px-3 py-2">{t.assigned}</td>
                  <td className="px-3 py-2">{t.submitted}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap space-x-2">
                    {!t.is_published && <Link to={`/admin/tests/${t.id}`} className={`${btn} inline-block`}>Edit</Link>}
                    {!t.is_published && <button onClick={() => publish(t)} className={btn}>Publish</button>}
                    {t.is_published && <button onClick={() => setAssigning(t)} className={btn}>Assign</button>}
                    {t.assigned > 0 && <button onClick={() => setViewing(t)} className={btn}>Results</button>}
                    <button onClick={() => remove(t)} disabled={t.assigned > 0} title={t.assigned > 0 ? 'Applicants are assigned, so this test cannot be deleted' : ''}
                      className="text-sm border border-red-300 text-red-700 rounded-md px-2 py-1 hover:bg-red-50 disabled:opacity-40">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && loaded.tests.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-10 text-center text-slate-600">No tests yet. Click “New test” to create one.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </main>

      {assigning && (
        <AssignDialog paper={assigning} onClose={() => setAssigning(null)} onExpired={expire}
          onDone={() => { setAssigning(null); setReload((n) => n + 1) }} />
      )}
      {viewing && <ResultsDialog paper={viewing} onClose={() => setViewing(null)} onExpired={expire} />}
    </div>
  )
}
