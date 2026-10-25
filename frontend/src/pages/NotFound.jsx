import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Any address the app has no page for (the catch-all route in App.jsx). Without it React Router renders
// nothing, so a mistyped or outdated link showed a blank white page. Same look as /info/<unknown>.
export default function NotFound() {
  const { pathname } = useLocation()
  const { isAuthenticated } = useAuth()

  const staff = pathname.startsWith('/admin')
  const back = staff
    ? { to: '/admin/dashboard', label: 'Back to the staff portal' }
    : isAuthenticated
      ? { to: '/dashboard', label: 'Back to dashboard' }
      : { to: '/', label: 'Back to home' }

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <Link to={back.to} className="text-sm text-gray-600 underline">
        &larr; {back.label}
      </Link>
      <h1 className="text-2xl font-semibold mt-4 mb-2">Page not found</h1>
      <p className="text-gray-600">
        There is no page at this address. It may have been mistyped, or the link may be out of date.
      </p>
    </div>
  )
}
