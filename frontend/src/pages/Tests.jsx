import AppHeader from '../components/AppHeader'

// SRD FR-10: the applicant's list of assigned aptitude tests. Owner: Person 1.
// Placeholder from the scaffold: replace the body, keep the route (/tests) and the header.
export default function Tests() {
  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold mb-2">Aptitude tests</h1>
        <p className="text-gray-600">Coming soon.</p>
      </div>
    </div>
  )
}
