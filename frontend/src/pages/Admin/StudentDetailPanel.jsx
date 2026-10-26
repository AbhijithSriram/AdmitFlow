import { useEffect, useState } from 'react'
import { adminApi } from '../../api/client'
import StatusBadge from '../../components/StatusBadge'
import { orderedRows } from '../../utils/fieldLabels'
import { errorMessage, formatDate, formatDateTime } from './adminUtils'

const STEP_TITLES = { 1: 'Personal details', 2: 'Address', 3: 'Programme preference', 4: 'Academic details', 5: 'Entrance / test details', 6: 'ID proof details' }
const APTITUDE_STATUS = { ASSIGNED: 'Assigned, not started', IN_PROGRESS: 'In progress', SUBMITTED: 'Submitted' }
const DOC_LABELS = { photo: 'Photo', signature: 'Signature', id_proof: 'ID proof', application_pdf: 'Application PDF' }

const show = (v) => {
  if (v === null || v === '' || v === undefined) return '—'
  if (v === true) return 'Yes'
  if (v === false) return 'No'
  return typeof v === 'object' ? JSON.stringify(v) : String(v)
}

function Fields({ rows }) {
  return (
    <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-1 text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-slate-600">{label}</dt>
          <dd className="text-slate-900 break-words">{show(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function Section({ title, children }) {
  return (
    <section className="py-4 border-b border-slate-200 last:border-0">
      <h3 className="text-sm font-semibold text-slate-900 mb-2">{title}</h3>
      {children}
    </section>
  )
}

/** Slide-over with the full application for one student (FR-7.2: click a row). */
export default function StudentDetailPanel({ studentId, onClose, onDelete, onUnauthorised }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    // State starts fresh for each applicant because the parent renders this with key={studentId}.
    adminApi
      .getStudent(studentId)
      .then((res) => !cancelled && setDetail(res.data.data))
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) onUnauthorised()
        else setError(errorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [studentId, onUnauthorised])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const s = detail?.student
  const app = detail?.application

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/40" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside role="dialog" aria-modal="true" aria-label="Applicant detail" className="w-full max-w-xl bg-white h-full overflow-y-auto p-6">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-900">{s ? s.full_name : 'Applicant'}</h2>
          <button onClick={onClose} className="text-sm text-slate-700 underline">
            Close
          </button>
        </div>

        {error && (
          <p role="alert" className="text-sm font-medium text-red-700 mt-4">
            {error}
          </p>
        )}
        {!detail && !error && <p className="text-sm text-slate-600 mt-4">Loading applicant…</p>}

        {detail && (
          <>
            <Section title="Account">
              <Fields
                rows={[
                  ['Email', s.email],
                  ['Phone', s.phone],
                  ['Date of birth', formatDate(s.date_of_birth)],
                  ['Gender', s.gender],
                  ['Email verified', s.email_verified ? 'Yes' : 'No'],
                  ['Registered', formatDateTime(s.created_at)],
                ]}
              />
            </Section>

            <Section title="Application">
              {!app ? (
                <p className="text-sm text-slate-600">This applicant has not started an application.</p>
              ) : (
                <>
                  <div className="mb-3">
                    <StatusBadge status={app.status} />
                  </div>
                  <Fields
                    rows={[
                      ['Programme', app.programme],
                      ['Specialisation', app.specialisation],
                      ['Guidelines accepted', formatDateTime(app.guidelines_accepted_at)],
                      ['Last updated', formatDateTime(app.updated_at)],
                    ]}
                  />
                </>
              )}
            </Section>

            {app && (
              <Section title="Documents">
                <ul className="text-sm flex flex-col gap-1">
                  {Object.entries(app.documents).map(([key, doc]) => (
                    <li key={key} className="flex gap-3">
                      <span className="w-32 text-slate-600">{DOC_LABELS[key]}</span>
                      {!doc.present ? (
                        <span className="text-slate-500">Not uploaded</span>
                      ) : doc.url ? (
                        <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-indigo-700 underline">
                          Open (link expires in 15 minutes)
                        </a>
                      ) : (
                        <span className="text-red-700">{doc.error}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {Object.entries(detail.steps).map(([n, data]) => (
              <Section key={n} title={STEP_TITLES[n] || `Step ${n}`}>
                <Fields rows={orderedRows(Number(n), data)} />
              </Section>
            ))}

            {detail.aptitude?.length > 0 && (
              <Section title="Aptitude test">
                <ul className="text-sm flex flex-col gap-1">
                  {detail.aptitude.map((t) => (
                    <li key={t.paper_id} className="flex flex-wrap gap-x-4">
                      <span className="font-medium">{t.title}</span>
                      <span>{APTITUDE_STATUS[t.status]}</span>
                      {t.score !== null && (
                        <span>
                          {t.score} / {t.total_marks} ({t.passed ? 'passed' : 'not passed'}; pass mark {t.pass_marks})
                        </span>
                      )}
                      {t.submitted_at && <span className="text-slate-600">{formatDateTime(t.submitted_at)}</span>}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {detail.payments.length > 0 && (
              <Section title="Payment attempts">
                <ul className="text-sm flex flex-col gap-1">
                  {detail.payments.map((p) => (
                    <li key={p.id} className="flex flex-wrap gap-x-4">
                      <span className="font-medium">{p.status}</span>
                      <span>₹{p.amount}</span>
                      <span className="text-slate-600">{formatDateTime(p.created_at)}</span>
                      <span className="text-slate-600">{p.razorpay_payment_id || p.razorpay_order_id || ''}</span>
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            <div className="pt-4">
              <button
                onClick={() => onDelete({ id: s.id, name: s.full_name, email: s.email })}
                className="px-4 py-2 rounded-md border border-red-300 text-red-700 font-medium hover:bg-red-50"
              >
                Delete this applicant…
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
