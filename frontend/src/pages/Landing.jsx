import { Link } from 'react-router-dom'
import { INSTITUTION_NAME, KEY_DATES, PROGRAMMES as PROGRAMME_SPECIALISATIONS } from '../content/institution'

// Same list the application form offers in Step 4, so the two can never disagree.
const PROGRAMMES = Object.entries(PROGRAMME_SPECIALISATIONS).map(([name, specialisations]) => ({
  name,
  detail: specialisations.join(', '),
}))

// FR-1: landing page — institution info, programmes, key dates, login/register CTAs.
export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <span className="text-xl font-semibold">{INSTITUTION_NAME}</span>
        <nav className="flex gap-3">
          <Link to="/login" className="px-4 py-2 rounded bg-black text-white">
            Login
          </Link>
          <Link to="/signup" className="px-4 py-2 rounded border border-black">
            Register
          </Link>
        </nav>
      </header>

      <main className="flex-1 w-full max-w-4xl mx-auto px-6 py-12 flex flex-col gap-12">
        <section className="text-center flex flex-col gap-4">
          <h1 className="text-4xl font-semibold">Apply to the college of your choice</h1>
          <p className="text-gray-600 max-w-xl mx-auto">
            Integrated College Admissions &amp; Evaluation Portal. Register, complete one
            application form, pay the fee online and track your status — all in one place.
          </p>
          <div className="flex justify-center gap-4 pt-2">
            <Link to="/signup" className="px-6 py-3 rounded bg-black text-white">
              Start your application
            </Link>
            <Link to="/login" className="px-6 py-3 rounded border border-black">
              Continue an application
            </Link>
          </div>
          <p className="text-sm">
            <a href="/brochure.pdf" target="_blank" rel="noopener noreferrer" className="underline">
              Download the information brochure (PDF)
            </a>
          </p>
        </section>

        <section aria-labelledby="programmes-heading" className="flex flex-col gap-4">
          <h2 id="programmes-heading" className="text-2xl font-semibold">
            Programmes
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PROGRAMMES.map((programme) => (
              <li key={programme.name} className="border border-gray-200 rounded p-4">
                <h3 className="font-semibold">{programme.name}</h3>
                <p className="text-sm text-gray-600">{programme.detail}</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="dates-heading" className="flex flex-col gap-4">
          <h2 id="dates-heading" className="text-2xl font-semibold">
            Key dates
          </h2>
          <dl className="grid gap-4 sm:grid-cols-2">
            {KEY_DATES.map((item) => (
              <div key={item.label} className="flex justify-between border-b border-gray-200 py-2">
                <dt className="text-gray-600">{item.label}</dt>
                <dd className="font-medium">{item.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      </main>

      <footer className="px-6 py-4 border-t border-gray-200 text-center text-sm text-gray-500">
        &copy; AdmitFlow. Need help? Contact the admissions office.
      </footer>
    </div>
  )
}
