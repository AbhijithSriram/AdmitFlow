import StatusBadge from '../components/StatusBadge'

// FR-5: applicant dashboard — status badge, quick actions, navigation links.
export default function Dashboard() {
  return (
    <div className="min-h-screen p-6">
      <h1 className="text-2xl font-semibold mb-4">Your Application</h1>
      <StatusBadge status="NOT_STARTED" />
      {/* TODO: quick-action buttons, nav links */}
    </div>
  )
}
