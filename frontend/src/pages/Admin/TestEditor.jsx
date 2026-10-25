import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { adminTestsApi } from '../../api/client'
import { errorMessage } from './adminUtils'
import { useAdminSession } from './useAdminSession'

// SRD FR-10: create or edit an aptitude test and its questions.
// Serves two routes: /admin/tests/new (no paperId) and /admin/tests/:paperId (edit).
const field = 'border border-slate-400 rounded-md px-3 py-2 text-sm bg-white focus:outline-2 focus:outline-indigo-600'
const btn = 'text-sm border border-slate-400 rounded-md px-2 py-1 hover:bg-slate-100 disabled:opacity-40'
const OPTIONS = ['a', 'b', 'c', 'd']

const blankQuestion = (key) => ({ key, question_text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: '', marks: '1' })

function Page({ title, children }) {
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
      <main className="max-w-4xl mx-auto p-6">
        <Link to="/admin/tests" className="text-sm underline">&larr; All tests</Link>
        <h1 className="text-2xl font-semibold text-slate-900 my-3">{title}</h1>
        {children}
      </main>
    </div>
  )
}

function EditorForm({ initial, paperId, onExpired }) {
  const navigate = useNavigate()
  const nextKey = useRef(initial.questions.length + 1)
  const [form, setForm] = useState(initial)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const total = form.questions.reduce((sum, q) => sum + (Number.parseInt(q.marks, 10) || 0), 0)
  const setQuestion = (i, patch) =>
    setForm((f) => ({ ...f, questions: f.questions.map((q, n) => (n === i ? { ...q, ...patch } : q)) }))
  const addQuestion = () => setForm((f) => ({ ...f, questions: [...f.questions, blankQuestion(nextKey.current++)] }))
  const removeQuestion = (i) => setForm((f) => ({ ...f, questions: f.questions.filter((_, n) => n !== i) }))
  const moveQuestion = (i, by) =>
    setForm((f) => {
      const qs = [...f.questions]
      ;[qs[i], qs[i + by]] = [qs[i + by], qs[i]]
      return { ...f, questions: qs }
    })

  async function save(e) {
    e.preventDefault()
    setError('')
    const duration = Number(form.duration_minutes)
    const pass = Number(form.pass_marks)
    if (!Number.isInteger(duration) || duration < 1) return setError('Enter the duration as a whole number of minutes.')
    if (!Number.isInteger(pass) || pass < 0) return setError('Enter the pass marks as a whole number.')
    if (pass > total) return setError(`Pass marks (${pass}) cannot be more than the total marks (${total}).`)
    const payload = {
      title: form.title,
      duration_minutes: duration,
      total_marks: total, // always the sum of the questions, so publishing never fails on a mismatch
      pass_marks: pass,
      questions: form.questions.map((q) => ({
        question_text: q.question_text,
        option_a: q.option_a,
        option_b: q.option_b,
        option_c: q.option_c,
        option_d: q.option_d,
        correct_option: q.correct_option,
        marks: Number.parseInt(q.marks, 10),
      })),
    }
    setBusy(true)
    try {
      await (paperId ? adminTestsApi.update(paperId, payload) : adminTestsApi.create(payload))
      navigate('/admin/tests')
    } catch (err) {
      if (err?.response?.status === 401) onExpired()
      else setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-5">
      <section className="bg-white border border-slate-200 rounded-lg p-5 grid gap-4 md:grid-cols-[2fr_1fr_1fr]">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Title
          <input className={`${field} font-normal`} value={form.title} maxLength={255} required
            onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Time allowed (minutes)
          <input className={`${field} font-normal`} type="number" min="1" max="600" required value={form.duration_minutes}
            onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
          Pass marks
          <input className={`${field} font-normal`} type="number" min="0" required value={form.pass_marks}
            onChange={(e) => setForm({ ...form, pass_marks: e.target.value })} />
        </label>
        <p className="md:col-span-3 text-sm text-slate-700">
          Total marks: <strong>{total}</strong> <span className="text-slate-500">(the sum of the questions’ marks)</span>
        </p>
      </section>

      {form.questions.map((q, i) => (
        <fieldset key={q.key} className="bg-white border border-slate-200 rounded-lg p-5">
          <legend className="px-1 text-sm font-semibold text-slate-900">Question {i + 1}</legend>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
            Question text
            <textarea className={`${field} font-normal`} rows={2} required value={q.question_text}
              onChange={(e) => setQuestion(i, { question_text: e.target.value })} />
          </label>
          <div className="grid gap-2 mt-3 md:grid-cols-2">
            {OPTIONS.map((k) => (
              <div key={k} className="flex items-center gap-2">
                <input type="radio" name={`correct-${q.key}`} required aria-label={`Option ${k.toUpperCase()} is the correct answer`}
                  checked={q.correct_option === k.toUpperCase()} onChange={() => setQuestion(i, { correct_option: k.toUpperCase() })} />
                <span className="text-sm font-semibold w-4">{k.toUpperCase()}</span>
                <input className={`${field} flex-1`} required maxLength={500} aria-label={`Option ${k.toUpperCase()} text`}
                  value={q[`option_${k}`]} onChange={(e) => setQuestion(i, { [`option_${k}`]: e.target.value })} />
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-1">Select the circle next to the correct option.</p>
          <div className="flex flex-wrap items-center gap-3 mt-3">
            <label className="text-sm font-medium text-slate-800">
              Marks{' '}
              <input className={`${field} w-20 font-normal`} type="number" min="1" max="100" required value={q.marks}
                onChange={(e) => setQuestion(i, { marks: e.target.value })} />
            </label>
            <span className="ml-auto flex gap-2">
              <button type="button" className={btn} disabled={i === 0} onClick={() => moveQuestion(i, -1)}>Move up</button>
              <button type="button" className={btn} disabled={i === form.questions.length - 1} onClick={() => moveQuestion(i, 1)}>Move down</button>
              <button type="button" className="text-sm border border-red-300 text-red-700 rounded-md px-2 py-1 hover:bg-red-50 disabled:opacity-40"
                disabled={form.questions.length === 1} onClick={() => removeQuestion(i)}>Remove</button>
            </span>
          </div>
        </fieldset>
      ))}

      <button type="button" onClick={addQuestion} className="self-start px-4 py-2 rounded-md border border-slate-400 bg-white hover:bg-slate-50">
        + Add question
      </button>

      {error && <p role="alert" className="text-sm font-medium text-red-700">{error}</p>}
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy} className="px-5 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700 disabled:opacity-50">
          {busy ? 'Saving…' : 'Save as draft'}
        </button>
        <span className="text-sm text-slate-600">You publish it from the tests list once it is ready.</span>
      </div>
    </form>
  )
}

export default function TestEditor() {
  const { paperId } = useParams()
  const { status, expire } = useAdminSession()
  const [loaded, setLoaded] = useState({ id: null, paper: null, error: '' })

  useEffect(() => {
    if (!paperId || status !== 'authed') return undefined
    let cancelled = false
    adminTestsApi
      .get(paperId)
      .then((res) => !cancelled && setLoaded({ id: paperId, paper: res.data.data, error: '' }))
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) expire()
        else setLoaded({ id: paperId, paper: null, error: errorMessage(err) })
      })
    return () => {
      cancelled = true
    }
  }, [paperId, status, expire])

  if (status === 'loading') return <p className="p-10 text-center text-slate-600">Checking your session…</p>
  if (status === 'anon') return <Navigate to="/admin/auth" replace />

  if (!paperId) {
    const initial = { title: '', duration_minutes: '30', pass_marks: '', questions: [blankQuestion(1)] }
    return <Page title="New test"><EditorForm initial={initial} onExpired={expire} /></Page>
  }

  if (loaded.id !== paperId) return <Page title="Edit test"><p className="text-slate-600">Loading test…</p></Page>
  if (loaded.error) return <Page title="Edit test"><p role="alert" className="text-red-700 font-medium">{loaded.error}</p></Page>
  if (loaded.paper.is_published) {
    return (
      <Page title={loaded.paper.title}>
        <p className="text-slate-800">This test is published, so it can no longer be edited. Create a new test if you need a different version.</p>
      </Page>
    )
  }
  const p = loaded.paper
  const initial = {
    title: p.title, duration_minutes: String(p.duration_minutes), pass_marks: String(p.pass_marks),
    questions: p.questions.map((q, n) => ({ ...blankQuestion(n + 1), ...q, marks: String(q.marks) })),
  }
  return <Page title="Edit test"><EditorForm key={paperId} initial={initial} paperId={paperId} onExpired={expire} /></Page>
}
