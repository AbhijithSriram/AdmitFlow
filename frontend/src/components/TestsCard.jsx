import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { studentTestsApi } from '../api/client'
import { listErrorMessage } from './testsMessages'

// Dashboard card listing the applicant's assigned aptitude tests (SRD FR-10). Owner: Person 1.
// Person 3 mounts <TestsCard /> in Dashboard.jsx (for PAID applicants only); this file is ours.
// The list pieces are exported for the full /tests page. Scores are never shown to students
// (team decision 3): the API does not send them, and nothing here would display one.

const STATUS = {
  ASSIGNED: { label: 'Not started', badge: 'bg-gray-200 text-gray-800', action: 'Start' },
  IN_PROGRESS: { label: 'In progress', badge: 'bg-yellow-100 text-yellow-800', action: 'Resume' },
  SUBMITTED: { label: 'Done', badge: 'bg-green-100 text-green-800', action: null },
}

// The server sends the deadline in UTC with a trailing Z, so this shows it in the student's own time.
const formatDeadline = (iso) =>
  new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

export function useAssignedTests() {
  const [tests, setTests] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    studentTestsApi
      .list()
      .then((response) => {
        if (!cancelled) setTests(response.data.data.tests)
      })
      .catch((err) => {
        if (!cancelled) setError(listErrorMessage(err.response?.status))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { tests, loading: tests === null && error === null, error }
}

export function TestList({ tests }) {
  return (
    <ul className="divide-y border rounded">
      {tests.map((test) => {
        const status = STATUS[test.status] ?? STATUS.ASSIGNED
        return (
          <li key={test.paper_id} className="flex flex-wrap items-center gap-3 p-3">
            <div className="flex-1 min-w-48">
              <p className="font-medium">{test.title}</p>
              <p className="text-sm text-gray-600">
                {test.question_count} questions · {test.duration_minutes} minutes
                {test.status === 'IN_PROGRESS' && test.deadline && <> · ends {formatDeadline(test.deadline)}</>}
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${status.badge}`}>{status.label}</span>
            {status.action && (
              <Link to={`/tests/${test.paper_id}`} className="px-4 py-2 rounded bg-black text-white">
                {status.action}
              </Link>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export default function TestsCard() {
  const { tests, loading, error } = useAssignedTests()

  if (loading) return null
  if (error) return <p className="text-red-600 text-sm mt-6">{error}</p>
  if (tests.length === 0) return null // nothing assigned yet: keep the dashboard uncluttered

  return (
    <section className="mt-8">
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="text-lg font-semibold">Aptitude tests</h2>
        <Link to="/tests" className="text-sm underline text-gray-600">
          View all
        </Link>
      </div>
      <TestList tests={tests} />
    </section>
  )
}
