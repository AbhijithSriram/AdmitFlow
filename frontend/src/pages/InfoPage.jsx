import { Link, useParams } from 'react-router-dom'
import {
  ABOUT,
  APPLICATION_FEE_INR,
  CONTACT,
  DATES_NOTE,
  DOCUMENTS_AT_ADMISSION,
  ELIGIBILITY,
  GUIDELINES,
  KEY_DATES,
  PROGRAMMES,
} from '../content/institution'
import { useAuth } from '../context/AuthContext'

// FR-5 navigation targets: Eligibility & Fee Structure, Important Dates, Guidelines, Contact.
// Public pages (no login needed). The text lives in src/content/institution.js.
const PAGES = {
  eligibility: {
    title: 'Eligibility & Fee Structure',
    render: () => (
      <>
        <h2 className="text-lg font-semibold mb-2">Who can apply</h2>
        <ul className="list-disc pl-5 flex flex-col gap-1 mb-6">
          {ELIGIBILITY.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <h2 className="text-lg font-semibold mb-2">Programmes</h2>
        <ul className="list-disc pl-5 flex flex-col gap-1 mb-6">
          {Object.entries(PROGRAMMES).map(([name, specialisations]) => (
            <li key={name}>
              <strong>{name}</strong>: {specialisations.join(', ')}
            </li>
          ))}
        </ul>
        <h2 className="text-lg font-semibold mb-2">Original documents checked at admission</h2>
        <ul className="list-disc pl-5 flex flex-col gap-1 mb-6">
          {DOCUMENTS_AT_ADMISSION.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <h2 className="text-lg font-semibold mb-2">Fee</h2>
        <table className="w-full max-w-sm text-sm border border-gray-200">
          <tbody>
            <tr className="border-b border-gray-200">
              <td className="px-3 py-2">Application fee</td>
              <td className="px-3 py-2 text-right font-medium">₹{APPLICATION_FEE_INR.toLocaleString('en-IN')}</td>
            </tr>
            <tr>
              <td className="px-3 py-2">Refund</td>
              <td className="px-3 py-2 text-right">Non-refundable</td>
            </tr>
          </tbody>
        </table>
      </>
    ),
  },
  dates: {
    title: 'Important Dates',
    render: () => (
      <>
        <dl className="grid gap-2 max-w-lg">
          {KEY_DATES.map((item) => (
            <div key={item.label} className="flex justify-between gap-4 border-b border-gray-200 py-2">
              <dt className="text-gray-600">{item.label}</dt>
              <dd className="font-medium text-right">{item.value}</dd>
            </div>
          ))}
        </dl>
        {DATES_NOTE && <p className="text-sm text-gray-500 mt-3">{DATES_NOTE}</p>}
      </>
    ),
  },
  guidelines: {
    title: 'Application Guidelines',
    render: () => (
      <ol className="list-decimal pl-5 flex flex-col gap-2">
        {GUIDELINES.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ol>
    ),
  },
  contact: {
    title: 'Contact',
    render: () => (
      <>
        <dl className="grid grid-cols-[7rem_1fr] gap-y-2 text-sm">
          {CONTACT.email && (
            <>
              <dt className="text-gray-600">Email</dt>
              <dd>
                <a className="underline" href={`mailto:${CONTACT.email}`}>
                  {CONTACT.email}
                </a>
              </dd>
            </>
          )}
          {CONTACT.phone && (
            <>
              <dt className="text-gray-600">Phone</dt>
              <dd>{CONTACT.phone}</dd>
            </>
          )}
          {CONTACT.address && (
            <>
              <dt className="text-gray-600">Address</dt>
              <dd>{CONTACT.address}</dd>
            </>
          )}
          {CONTACT.hours && (
            <>
              <dt className="text-gray-600">Office hours</dt>
              <dd>{CONTACT.hours}</dd>
            </>
          )}
        </dl>
        {CONTACT.note && <p className="text-sm text-gray-600 mt-4 max-w-xl">{CONTACT.note}</p>}
      </>
    ),
  },
  about: {
    title: 'About this project',
    render: () => (
      <div className="flex flex-col gap-3 max-w-2xl">
        {ABOUT.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    ),
  },
}

export default function InfoPage() {
  const { topic } = useParams()
  const { isAuthenticated } = useAuth()
  const page = PAGES[topic]

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <Link to={isAuthenticated ? '/dashboard' : '/'} className="text-sm text-gray-600 underline">
        &larr; {isAuthenticated ? 'Back to dashboard' : 'Back to home'}
      </Link>
      {page ? (
        <>
          <h1 className="text-2xl font-semibold mt-4 mb-4">{page.title}</h1>
          {page.render()}
        </>
      ) : (
        <h1 className="text-2xl font-semibold mt-4">Page not found</h1>
      )}
    </div>
  )
}
