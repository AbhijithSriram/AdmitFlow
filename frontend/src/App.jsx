import { Route, Routes } from 'react-router-dom'
import AdminDashboard from './pages/Admin/AdminDashboard'
import AdminLogin from './pages/Admin/AdminLogin'
import ApplicationForm from './pages/ApplicationForm'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import OtpVerification from './pages/OtpVerification'
import SetPassword from './pages/SetPassword'
import Signup from './pages/Signup'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/verify-otp" element={<OtpVerification />} />
      <Route path="/set-password" element={<SetPassword />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/application" element={<ApplicationForm />} />
      <Route path="/admin/auth" element={<AdminLogin />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
    </Routes>
  )
}
