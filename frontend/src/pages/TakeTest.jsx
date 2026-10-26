import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { studentTestsApi } from '../api/client'
import AppHeader from '../components/AppHeader'
import { NOT_PAID } from '../components/testsMessages'

// SRD FR-10: the timed test page. Owner: Person 1.
// The server owns the timer: start returns seconds_left, and the countdown runs from it on
// performance.now() (elapsed time, unaffected by changing the computer's clock). Every save and
// every return to the tab re-syncs it from the server, which also refuses late answers itself.
// A 409 from start, save or submit means the attempt is closed: we show "test over", not an error.

const OPTIONS = ['A', 'B', 'C', 'D']
const WARN_AT_SECONDS = 60
const RETRY_SAVE_MS = 5000

const formatClock = (seconds) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = String(seconds % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
}

const formatTime = (iso) => new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })

const START_ERRORS = {
  403: NOT_PAID,
  404: 'This test was not found, or it is not assigned to you.',
}

export default function TakeTest() {
  const { paperId } = useParams()
  // loading | taking | submitting | submitted | over | error
  const [phase, setPhaseState] = useState('loading')
  const [message, setMessage] = useState(null)
  const [test, setTest] = useState(null) // { paper, questions, deadline }
  const [answers, setAnswers] = useState({})
  const [current, setCurrent] = useState(0)
  const [remaining, setRemaining] = useState(null) // whole seconds
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | failed
  const [confirming, setConfirming] = useState(false)

  const endAtRef = useRef(null) // performance.now() value at which time runs out
  const pendingRef = useRef({}) // picks not yet saved: { question_id: option }
  const queueRef = useRef(Promise.resolve())
  const phaseRef = useRef('loading') // the same phase, readable from timers and async code

  const setPhase = useCallback((next) => {
    phaseRef.current = next
    setPhaseState(next)
  }, [])

  // Re-sync with the server. Never move the end later than it already is: a stale reply
  // (network delay) must not add time, while a sleeping laptop catching up must take it away.
  const anchor = useCallback((secondsLeft) => {
    const endAt = performance.now() + secondsLeft * 1000
    endAtRef.current = endAtRef.current === null ? endAt : Math.min(endAtRef.current, endAt)
  }, [])

  const endAsOver = useCallback(() => {
    pendingRef.current = {}
    setConfirming(false)
    setPhase('over')
  }, [setPhase])

  const handleStart = useCallback(
    (response) => {
      const data = response.data.data
      anchor(data.seconds_left)
      return data
    },
    [anchor],
  )

  // Load (or resume) the attempt. start is idempotent: a refresh gets the same deadline and the
  // answers saved so far.
  useEffect(() => {
    let cancelled = false
    studentTestsApi
      .start(paperId)
      .then((response) => {
        if (cancelled) return
        const data = handleStart(response)
        setTest({ paper: data.paper, questions: data.questions, deadline: data.deadline })
        setAnswers(data.answers ?? {})
        setPhase('taking')
      })
      .catch((err) => {
        if (cancelled) return
        const status = err.response?.status
        if (status === 409) {
          setPhase('over')
        } else {
          setMessage(START_ERRORS[status] ?? 'Could not load the test. Check your connection and refresh.')
          setPhase('error')
        }
      })
    return () => {
      cancelled = true
    }
  }, [paperId, handleStart, setPhase])

  // Coming back to the tab (or waking the laptop): ask the server how much time is really left.
  useEffect(() => {
    if (phase !== 'taking') return undefined
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      studentTestsApi
        .start(paperId)
        .then(handleStart)
        .catch((err) => {
          if (err.response?.status === 409) endAsOver()
        })
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [phase, paperId, handleStart, endAsOver])

  // Saves run one after another so they cannot overtake each other; each sends every pick made
  // since the last one. Resolves true when nothing is left unsaved.
  const flush = useCallback(() => {
    const run = async () => {
      const picks = pendingRef.current
      if (Object.keys(picks).length === 0) return true
      pendingRef.current = {}
      setSaveState('saving')
      try {
        const response = await studentTestsApi.saveAnswers(paperId, picks)
        anchor(response.data.data.seconds_left)
        setSaveState(Object.keys(pendingRef.current).length > 0 ? 'saving' : 'saved')
        return true
      } catch (err) {
        if (err.response?.status === 409) {
          endAsOver()
          return false
        }
        pendingRef.current = { ...picks, ...pendingRef.current } // a newer pick for the same question wins
        setSaveState('failed')
        return false
      }
    }
    queueRef.current = queueRef.current.then(run)
    return queueRef.current
  }, [paperId, anchor, endAsOver])

  // A failed save is retried until it goes through (or time runs out).
  useEffect(() => {
    if (saveState !== 'failed' || phase !== 'taking') return undefined
    const id = setTimeout(flush, RETRY_SAVE_MS)
    return () => clearTimeout(id)
  }, [saveState, phase, flush])

  // Warn before leaving with an answer that has not reached the server yet.
  useEffect(() => {
    const onBeforeUnload = (event) => {
      if (Object.keys(pendingRef.current).length > 0) event.preventDefault()
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [])

  const pick = (questionId, option) => {
    if (phase !== 'taking') return
    setAnswers((prev) => ({ ...prev, [questionId]: option }))
    pendingRef.current = { ...pendingRef.current, [questionId]: option }
    flush()
  }

  const submit = useCallback(
    async ({ auto }) => {
      if (phaseRef.current !== 'taking') return
      setConfirming(false)
      setPhase('submitting')
      setMessage(null)
      const saved = await flush()
      if (phaseRef.current === 'over') return
      if (!saved && !auto) {
        setMessage("Some answers aren't saved yet. Check your connection and try again.")
        setPhase('taking')
        return
      }
      try {
        await studentTestsApi.submit(paperId)
        setPhase('submitted')
      } catch (err) {
        if (err.response?.status === 409) {
          endAsOver()
        } else {
          setMessage('Could not submit. Check your connection and try again.')
          setPhase('taking')
        }
      }
    },
    [paperId, flush, endAsOver, setPhase],
  )

  // Countdown from the anchored end time; at 0:00 it submits whatever has been saved.
  useEffect(() => {
    if (phase !== 'taking' && phase !== 'submitting') return undefined
    const tick = () => {
      if (endAtRef.current === null) return
      const left = Math.max(0, Math.ceil((endAtRef.current - performance.now()) / 1000))
      setRemaining(left)
      if (left === 0 && phaseRef.current === 'taking') submit({ auto: true })
    }
    tick()
    const id = setInterval(tick, 250)
    return () => clearInterval(id)
  }, [phase, submit])

  if (phase === 'loading') {
    return (
      <Shell>
        <p>Loading the test…</p>
      </Shell>
    )
  }

  if (phase === 'error') {
    return (
      <Shell>
        <p className="text-red-600">{message}</p>
        <BackLink />
      </Shell>
    )
  }

  if (phase === 'submitted' || phase === 'over') {
    return (
      <Shell>
        <div className="border rounded p-6">
          <h1 className="text-2xl font-semibold mb-2">{phase === 'submitted' ? 'Test submitted' : 'This test is over'}</h1>
          <p className="text-gray-600">
            {phase === 'submitted'
              ? 'Your answers have been recorded.'
              : 'Time has run out or the test was already submitted. The answers saved before the deadline are the ones that count.'}
          </p>
        </div>
        <BackLink />
      </Shell>
    )
  }

  const { paper, questions, deadline } = test
  const question = questions[current]
  const answeredCount = questions.filter((q) => answers[q.id]).length
  const lowTime = remaining !== null && remaining <= WARN_AT_SECONDS
  const busy = phase === 'submitting'

  return (
    <Shell>
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-semibold">{paper.title}</h1>
          <p className="text-sm text-gray-600">
            {answeredCount} of {questions.length} answered · ends at {formatTime(deadline)}
          </p>
        </div>
        <div
          className={`text-right font-mono text-2xl tabular-nums ${lowTime ? 'text-red-600' : ''}`}
          aria-label="Time left"
        >
          {remaining === null ? '--:--' : formatClock(remaining)}
        </div>
      </div>

      {lowTime && (
        <p role="alert" className="mb-4 rounded border border-red-300 bg-red-50 px-4 py-2 text-red-800">
          Less than a minute left. Your answers are saved as you go, and the test submits itself at 0:00.
        </p>
      )}

      <nav aria-label="Questions" className="flex flex-wrap gap-2 mb-6">
        {questions.map((q, i) => (
          <button
            key={q.id}
            type="button"
            onClick={() => setCurrent(i)}
            aria-current={i === current ? 'step' : undefined}
            aria-label={`Question ${i + 1}${answers[q.id] ? ', answered' : ''}`}
            className={`w-10 h-10 rounded border text-sm font-medium ${
              answers[q.id] ? 'bg-green-100 border-green-600 text-green-900' : 'bg-white'
            } ${i === current ? 'ring-2 ring-black ring-offset-1' : ''}`}
          >
            {i + 1}
          </button>
        ))}
      </nav>

      <fieldset className="border rounded p-4" disabled={busy}>
        <legend className="px-1 text-sm text-gray-600">
          Question {current + 1} of {questions.length}
        </legend>
        <p className="mb-4 whitespace-pre-line">{question.text}</p>
        <div className="space-y-2">
          {OPTIONS.map((option) => (
            <label
              key={option}
              className={`flex items-start gap-3 rounded border p-3 cursor-pointer ${
                answers[question.id] === option ? 'border-black bg-gray-50' : ''
              }`}
            >
              <input
                type="radio"
                name={`q-${question.id}`}
                value={option}
                checked={answers[question.id] === option}
                onChange={() => pick(question.id, option)}
                className="mt-1"
              />
              <span>
                <span className="font-medium">{option}.</span> {question.options[option]}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-wrap items-center gap-3 mt-4">
        <button
          type="button"
          onClick={() => setCurrent((i) => i - 1)}
          disabled={current === 0}
          className="px-4 py-2 rounded border disabled:opacity-40"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={() => setCurrent((i) => i + 1)}
          disabled={current === questions.length - 1}
          className="px-4 py-2 rounded border disabled:opacity-40"
        >
          Next
        </button>
        <SaveStatus state={saveState} />
        <button
          type="button"
          onClick={() => setConfirming(true)}
          disabled={busy}
          className="ml-auto px-4 py-2 rounded bg-black text-white disabled:opacity-40"
        >
          {busy ? 'Submitting…' : 'Submit test'}
        </button>
      </div>

      {message && <p className="text-red-600 text-sm mt-3">{message}</p>}

      {confirming && (
        <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/40 p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded bg-white p-6">
            <h2 id="confirm-title" className="text-lg font-semibold mb-2">
              Submit the test?
            </h2>
            <p className="text-gray-600 mb-4">
              You have answered {answeredCount} of {questions.length} questions.
              {answeredCount < questions.length && ' Unanswered questions score nothing.'} You can't change your
              answers after submitting.
            </p>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setConfirming(false)} className="px-4 py-2 rounded border">
                Keep working
              </button>
              <button type="button" onClick={() => submit({ auto: false })} className="px-4 py-2 rounded bg-black text-white">
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="p-6 max-w-2xl mx-auto">{children}</div>
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/tests" className="inline-block mt-6 text-sm underline text-gray-600">
      Back to your tests
    </Link>
  )
}

function SaveStatus({ state }) {
  const text = {
    idle: '',
    saving: 'Saving…',
    saved: 'All answers saved',
    failed: 'Not saved yet. Retrying…',
  }[state]
  return (
    <span aria-live="polite" className={`text-sm ${state === 'failed' ? 'text-red-600' : 'text-gray-600'}`}>
      {text}
    </span>
  )
}
