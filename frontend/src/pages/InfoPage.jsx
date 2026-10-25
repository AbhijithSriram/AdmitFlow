import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useContent } from '../context/ContentContext'

// FR-5 navigation targets: Eligibility & Fee Structure, Important Dates, Guidelines, Contact, About.
// Public pages (no login needed). The text is the admin-editable site content (useContent).
const List = ({ items, fill, ordered = false }) => {
  const Tag = ordered ? 'ol' : 'ul'
  return (
    <Tag className={`${ordered ? 'list-decimal' : 'list-disc'} pl-5 flex flex-col gap-1 mb-6`}>
      {items.map((line, i) => (
        <li key={`${i}-${line}`}>{fill(line)}</li>
      ))}
    </Tag>
  )
}

const PAGES = {
  eligibility: {
    title: () => 'Eligibility & Fee Structure',
    render: ({ content, fill, feeText }) => (
      <>
        <h2 className="text-lg font-semibold mb-2">Who can apply</h2>
        <List items={content.eligibility} fill={fill} />
        <h2 className="text-lg font-semibold mb-2">Programmes</h2>
        <ul className="list-disc pl-5 flex flex-col gap-1 mb-6">
          {content.programmes.map((p) => (
            <li key={p.name}>
              <strong>{p.name}</strong>: {p.specialisations.join(', ')}
            </li>
          ))}
        </ul>
        {content.documents.length > 0 && (
          <>
            <h2 className="text-lg font-semibold mb-2">Original documents checked at admission</h2>
            <List items={content.documents} fill={fill} />
          </>
        )}
        <h2 className="text-lg font-semibold mb-2">Fee</h2>
        <table className="w-full max-w-sm text-sm border border-gray-200">
          <tbody>
            <tr className="border-b border-gray-200">
              <td className="px-3 py-2">Application fee</td>
              <td className="px-3 py-2 text-right font-medium">{feeText}</td>
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
    title: () => 'Important Dates',
    render: ({ content }) => (
      <>
        <dl className="grid gap-2 max-w-lg">
          {content.dates.items.map((item) => (
            <div key={item.label} className="flex justify-between gap-4 border-b border-gray-200 py-2">
              <dt className="text-gray-600">{item.label}</dt>
              <dd className="font-medium text-right">{item.value}</dd>
            </div>
          ))}
        </dl>
        {content.dates.note && <p className="text-sm text-gray-500 mt-3">{content.dates.note}</p>}
      </>
    ),
  },
  guidelines: {
    title: () => 'Application Guidelines',
    render: ({ content, fill }) => <List items={content.guidelines} fill={fill} ordered />,
  },
  contact: {
    title: () => 'Contact',
    render: ({ content }) => {
      const c = content.contact
      const rows = [
        ['Email', c.email && <a className="underline" href={`mailto:${c.email}`}>{c.email}</a>],
        ['Phone', c.phone],
        ['Address', c.address],
        ['Office hours', c.hours],
      ].filter(([, value]) => value)
      return (
        <>
          <dl className="grid grid-cols-[7rem_1fr] gap-y-2 text-sm">
            {rows.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-gray-600">{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          {c.note && <p className="text-sm text-gray-600 mt-4 max-w-xl">{c.note}</p>}
        </>
      )
    },
  },
  about: {
    title: ({ content }) => (content.demo_mode ? 'About this project' : `About ${content.institution.name}`),
    render: ({ content, fill }) => (
      <div className="flex flex-col gap-3 max-w-2xl">
        {content.institution.about.map((paragraph, i) => (
          <p key={i}>{fill(paragraph)}</p>
        ))}
      </div>
    ),
  },
}

export default function InfoPage() {
  const { topic } = useParams()
  const { isAuthenticated } = useAuth()
  const helpers = useContent()
  const page = PAGES[topic]

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <Link to={isAuthenticated ? '/dashboard' : '/'} className="text-sm text-gray-600 underline">
        &larr; {isAuthenticated ? 'Back to dashboard' : 'Back to home'}
      </Link>
      {page ? (
        <>
          <h1 className="text-2xl font-semibold mt-4 mb-4">{page.title(helpers)}</h1>
          {page.render(helpers)}
        </>
      ) : (
        <h1 className="text-2xl font-semibold mt-4">Page not found</h1>
      )}
    </div>
  )
}
