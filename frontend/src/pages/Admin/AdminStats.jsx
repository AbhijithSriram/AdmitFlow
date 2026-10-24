import { Link } from 'react-router-dom'

// SRD FR-11: the ERP statistics view (summary cards, programme table, registrations chart). Owner: Person 2.
// Placeholder from the scaffold: add useAdminSession (see AdminDashboard.jsx) when you build it.
export default function AdminStats() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Link to="/admin/dashboard" className="text-sm underline">&larr; Applicants</Link>
      <h1 className="text-2xl font-semibold my-3">Statistics</h1>
      <p className="text-gray-600">Coming soon.</p>
    </div>
  )
}
