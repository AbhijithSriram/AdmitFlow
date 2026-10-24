import { useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'

// SRD FR-10: the timed test page with a countdown that auto-submits at zero. Owner: Person 1.
// The deadline comes from the server (POST /api/student/tests/:paperId/start), never from the browser clock alone.
// Placeholder from the scaffold: replace the body, keep the route (/tests/:paperId) and the header.
export default function TakeTest() {
  const { paperId } = useParams()
  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold mb-2">Aptitude test</h1>
        <p className="text-gray-600">Test {paperId}: coming soon.</p>
      </div>
    </div>
  )
}
