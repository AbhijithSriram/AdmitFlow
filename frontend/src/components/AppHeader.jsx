import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useContent } from '../context/ContentContext'

// Top bar for the logged-in student pages: a way back to the dashboard and a way to log out.
export default function AppHeader() {
  const { student, logout } = useAuth()
  const { content } = useContent()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="flex items-center justify-between gap-4 px-6 py-3 border-b border-gray-200">
      <Link to="/dashboard" className="font-semibold">
        {content.institution.name}
      </Link>
      <nav className="flex items-center gap-4 text-sm">
        <Link to="/dashboard" className="underline">
          Dashboard
        </Link>
        {student?.full_name && <span className="text-gray-600 hidden sm:inline">{student.full_name}</span>}
        <button type="button" onClick={handleLogout} className="px-3 py-1 rounded border">
          Log out
        </button>
      </nav>
    </header>
  )
}
