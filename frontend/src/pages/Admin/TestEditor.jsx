import { Link, useParams } from 'react-router-dom'

// SRD FR-10: create or edit an aptitude test and its questions. Owner: Person 4.
// Serves two routes: /admin/tests/new (no paperId) and /admin/tests/:paperId (edit).
// Placeholder from the scaffold: add useAdminSession (see AdminDashboard.jsx) when you build it.
export default function TestEditor() {
  const { paperId } = useParams()
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Link to="/admin/tests" className="text-sm underline">&larr; Tests</Link>
      <h1 className="text-2xl font-semibold my-3">{paperId ? 'Edit test' : 'New test'}</h1>
      <p className="text-gray-600">Coming soon.</p>
    </div>
  )
}
