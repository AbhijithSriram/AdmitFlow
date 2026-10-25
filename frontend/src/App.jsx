import { Route, Routes } from 'react-router-dom'
import RequireAuth from './components/RequireAuth'
import AdminDashboard from './pages/Admin/AdminDashboard'
import AdminLogin from './pages/Admin/AdminLogin'
import AdminStats from './pages/Admin/AdminStats'
import AdminTests from './pages/Admin/AdminTests'
import TestEditor from './pages/Admin/TestEditor'
import ApplicationForm from './pages/ApplicationForm'
import Dashboard from './pages/Dashboard'
import InfoPage from './pages/InfoPage'
import Landing from './pages/Landing'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import OtpVerification from './pages/OtpVerification'
import SetPassword from './pages/SetPassword'
import Signup from './pages/Signup'
import TakeTest from './pages/TakeTest'
import Tests from './pages/Tests'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/verify-otp" element={<OtpVerification />} />
      <Route path="/set-password" element={<SetPassword />} />
      <Route path="/login" element={<Login />} />
      <Route path="/info/:topic" element={<InfoPage />} />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/application"
        element={
          <RequireAuth>
            <ApplicationForm />
          </RequireAuth>
        }
      />
      <Route
        path="/tests"
        element={
          <RequireAuth>
            <Tests />
          </RequireAuth>
        }
      />
      <Route
        path="/tests/:paperId"
        element={
          <RequireAuth>
            <TakeTest />
          </RequireAuth>
        }
      />
      <Route path="/admin/auth" element={<AdminLogin />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/admin/tests" element={<AdminTests />} />
      <Route path="/admin/tests/new" element={<TestEditor />} />
      <Route path="/admin/tests/:paperId" element={<TestEditor />} />
      <Route path="/admin/stats" element={<AdminStats />} />
      {/* Anything else: a "Page not found" page instead of a blank screen. Keep this last. */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
