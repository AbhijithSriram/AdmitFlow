import { Link } from 'react-router-dom'

// FR-1: landing page — institution info, programmes, key dates, login/register CTAs.
export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-4xl font-semibold">AdmitFlow</h1>
      <p className="text-gray-600 max-w-xl">
        Integrated College Admissions &amp; Evaluation Portal
      </p>
      <div className="flex gap-4">
        <Link to="/login" className="px-4 py-2 rounded bg-black text-white">
          Login
        </Link>
        <Link to="/signup" className="px-4 py-2 rounded border border-black">
          Register
        </Link>
      </div>
    </div>
  )
}
