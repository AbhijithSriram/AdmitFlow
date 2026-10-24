import { Link } from 'react-router-dom'

// SRD FR-10: admin list of aptitude tests, with publish and assign actions. Owner: Person 4.
// Placeholder from the scaffold: add useAdminSession (see AdminDashboard.jsx) when you build it.
export default function AdminTests() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Link to="/admin/dashboard" className="text-sm underline">&larr; Applicants</Link>
      <h1 className="text-2xl font-semibold my-3">Aptitude tests</h1>
      <p className="text-gray-600">Coming soon.</p>
    </div>
  )
}
