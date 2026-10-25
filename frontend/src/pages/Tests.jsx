import { Link } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { TestList, useAssignedTests } from '../components/TestsCard'

// SRD FR-10: the applicant's list of assigned aptitude tests. Owner: Person 1.
// A test whose time ran out is graded by the server when this list loads, so it already shows as Done.
export default function Tests() {
  const { tests, loading, error } = useAssignedTests()

  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold mb-2">Aptitude tests</h1>
        <p className="text-gray-600 mb-6">
          Each test is timed and can be taken once. Once you start, the timer keeps running even if you close the
          page.
        </p>

        {loading && <p>Loading your tests…</p>}
        {error && <p className="text-red-600">{error}</p>}
        {tests?.length === 0 && <p className="text-gray-600">No tests have been assigned to you yet.</p>}
        {tests?.length > 0 && <TestList tests={tests} />}

        <Link to="/dashboard" className="inline-block mt-6 text-sm underline text-gray-600">
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}
