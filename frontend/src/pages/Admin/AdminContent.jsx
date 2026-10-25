import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { adminContentApi, BROCHURE_URL } from '../../api/client'
import { useContent } from '../../context/ContentContext'
import { errorMessage, formatDateTime } from './adminUtils'
import ReauthDialog from './ReauthDialog'
import { useAdminSession } from './useAdminSession'
import { useKeepAlive } from './useKeepAlive'

// v1.1 FR-12: everything the public site and the application form show about the institution is
// edited here, so one deployment can be set up for any college without code changes. Each section
// saves on its own; the server validates it and writes an audit entry first.

const field = 'border border-slate-400 rounded-md px-3 py-2 text-sm bg-white font-normal focus:outline-2 focus:outline-indigo-600'
const smallBtn = 'text-xs border border-slate-400 rounded px-2 py-1 bg-white hover:bg-slate-100 disabled:opacity-40'

const move = (items, i, by) => {
  const next = [...items]
  ;[next[i], next[i + by]] = [next[i + by], next[i]]
  return next
}

// A list of texts with add / remove / reorder (guidelines, eligibility rules, documents, paragraphs).
function ListEditor({ items, onChange, addLabel, rows = 2, placeholder }) {
  return (
    <div className="flex flex-col gap-2">
      {items.map((item, i) => (
        <div key={i} className="flex gap-2 items-start">
          <span className="text-xs text-slate-500 w-6 pt-2 text-right">{i + 1}.</span>
          <textarea className={`${field} flex-1`} rows={rows} value={item} placeholder={placeholder}
            onChange={(e) => onChange(items.map((x, n) => (n === i ? e.target.value : x)))} />
          <div className="flex flex-col gap-1">
            <button type="button" className={smallBtn} disabled={i === 0} onClick={() => onChange(move(items, i, -1))} aria-label={`Move item ${i + 1} up`}>Up</button>
            <button type="button" className={smallBtn} disabled={i === items.length - 1} onClick={() => onChange(move(items, i, 1))} aria-label={`Move item ${i + 1} down`}>Down</button>
            <button type="button" className={`${smallBtn} text-red-700 border-red-300`} onClick={() => onChange(items.filter((_, n) => n !== i))} aria-label={`Remove item ${i + 1}`}>Remove</button>
          </div>
        </div>
      ))}
      <button type="button" className="self-start text-sm border border-slate-400 rounded-md px-3 py-1.5 bg-white hover:bg-slate-50" onClick={() => onChange([...items, ''])}>
        + {addLabel}
      </button>
    </div>
  )
}

const Text = ({ label, value, onChange, type = 'text', hint }) => (
  <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
    {label}
    <input type={type} className={field} value={value ?? ''} onChange={(e) => onChange(e.target.value)} />
    {hint && <span className="text-xs font-normal text-slate-500">{hint}</span>}
  </label>
)

// Each section: how to show it in the editor (from the stored value) and how to send it back.
const SECTIONS = [
  { key: 'institution', title: 'Institution', help: 'The name shown in headers, PDFs and emails, and the paragraphs on the About page.' },
  { key: 'contact', title: 'Contact', help: 'Shown on the Contact page and the brochure. Leave a box empty to hide that line.' },
  { key: 'dates', title: 'Important dates', help: 'Shown on the landing page, the Important Dates page and the brochure.' },
  { key: 'fee', title: 'Application fee', help: 'What applicants are charged at the payment step. Write {fee} in any text to show the current amount.' },
  { key: 'guidelines', title: 'Application guidelines', help: 'Shown before an applicant starts the form, and on the Guidelines page.' },
  { key: 'eligibility', title: 'Eligibility', help: 'Shown on the Eligibility & Fee Structure page and the brochure.' },
  { key: 'documents', title: 'Original documents checked at admission', help: 'Shown on the Eligibility page and the brochure.' },
  { key: 'programmes', title: 'Programmes and specialisations', help: 'What applicants can choose in Step 3. UG programmes ask for Class XII and X; PG programmes also ask for the UG degree. A programme or specialisation that applications use cannot be removed or renamed, and a new one gets 0 seats on the Statistics page.' },
  { key: 'suggestions', title: 'College and university suggestions', help: 'Offered as suggestions in Step 4 (applicants can still type any name). One per line.' },
]

const toEdit = (key, value) => {
  if (key === 'fee') return { amount_inr: String(value.amount_inr) }
  if (key === 'suggestions') return { colleges: value.colleges.join('\n'), universities: value.universities.join('\n') }
  if (key === 'contact') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, v ?? '']))
  if (key === 'dates') return { items: value.items, note: value.note ?? '' }
  return value
}

const fromEdit = (key, edit) => {
  if (key === 'fee') return { amount_inr: /^\d+$/.test(edit.amount_inr.trim()) ? Number(edit.amount_inr.trim()) : edit.amount_inr }
  if (key === 'suggestions') {
    const lines = (s) => s.split('\n').map((x) => x.trim()).filter(Boolean)
    return { colleges: lines(edit.colleges), universities: lines(edit.universities) }
  }
  return edit
}

function SectionBody({ sectionKey, edit, setEdit }) {
  switch (sectionKey) {
    case 'institution':
      return (
        <div className="flex flex-col gap-3">
          <Text label="Institution name" value={edit.name} onChange={(name) => setEdit({ ...edit, name })} />
          <div className="text-sm font-medium text-slate-800">About page paragraphs</div>
          <ListEditor items={edit.about} onChange={(about) => setEdit({ ...edit, about })} addLabel="Add paragraph" rows={3} />
        </div>
      )
    case 'contact':
      return (
        <div className="grid gap-3 md:grid-cols-2">
          <Text label="Email" type="email" value={edit.email} onChange={(email) => setEdit({ ...edit, email })} />
          <Text label="Phone" value={edit.phone} onChange={(phone) => setEdit({ ...edit, phone })} />
          <Text label="Address" value={edit.address} onChange={(address) => setEdit({ ...edit, address })} />
          <Text label="Office hours" value={edit.hours} onChange={(hours) => setEdit({ ...edit, hours })} />
          <label className="md:col-span-2 flex flex-col gap-1 text-sm font-medium text-slate-800">
            Note (shown under the contact details)
            <textarea className={field} rows={2} value={edit.note} onChange={(e) => setEdit({ ...edit, note: e.target.value })} />
          </label>
        </div>
      )
    case 'dates':
      return (
        <div className="flex flex-col gap-2">
          {edit.items.map((item, i) => (
            <div key={i} className="grid gap-2 md:grid-cols-[1fr_1fr_auto] items-end">
              <Text label={i === 0 ? 'What happens' : ''} value={item.label}
                onChange={(label) => setEdit({ ...edit, items: edit.items.map((x, n) => (n === i ? { ...x, label } : x)) })} />
              <Text label={i === 0 ? 'When' : ''} value={item.value}
                onChange={(value) => setEdit({ ...edit, items: edit.items.map((x, n) => (n === i ? { ...x, value } : x)) })} />
              <div className="flex gap-1 pb-1">
                <button type="button" className={smallBtn} disabled={i === 0} onClick={() => setEdit({ ...edit, items: move(edit.items, i, -1) })}>Up</button>
                <button type="button" className={smallBtn} disabled={i === edit.items.length - 1} onClick={() => setEdit({ ...edit, items: move(edit.items, i, 1) })}>Down</button>
                <button type="button" className={`${smallBtn} text-red-700 border-red-300`} onClick={() => setEdit({ ...edit, items: edit.items.filter((_, n) => n !== i) })}>Remove</button>
              </div>
            </div>
          ))}
          <button type="button" className="self-start text-sm border border-slate-400 rounded-md px-3 py-1.5 bg-white hover:bg-slate-50"
            onClick={() => setEdit({ ...edit, items: [...edit.items, { label: '', value: '' }] })}>+ Add date</button>
          <Text label="Note under the dates (optional)" value={edit.note} onChange={(note) => setEdit({ ...edit, note })} />
        </div>
      )
    case 'fee':
      return <Text label="Application fee (₹, whole rupees)" value={edit.amount_inr} onChange={(amount_inr) => setEdit({ amount_inr })} hint="Payments already made keep the amount they were made at." />
    case 'guidelines':
      return <ListEditor items={edit} onChange={setEdit} addLabel="Add guideline" />
    case 'eligibility':
      return <ListEditor items={edit} onChange={setEdit} addLabel="Add rule" />
    case 'documents':
      return <ListEditor items={edit} onChange={setEdit} addLabel="Add document" rows={1} />
    case 'programmes':
      return (
        <div className="flex flex-col gap-4">
          {edit.map((p, i) => {
            const setP = (patch) => setEdit(edit.map((x, n) => (n === i ? { ...x, ...patch } : x)))
            return (
              <fieldset key={i} className="border border-slate-200 rounded-lg p-4 flex flex-col gap-3">
                <legend className="px-1 text-sm font-semibold text-slate-900">Programme {i + 1}</legend>
                <div className="grid gap-3 md:grid-cols-[2fr_1fr_auto] items-end">
                  <Text label="Name" value={p.name} onChange={(name) => setP({ name })} />
                  <label className="flex flex-col gap-1 text-sm font-medium text-slate-800">
                    Level
                    <select className={field} value={p.level} onChange={(e) => setP({ level: e.target.value })}>
                      <option value="UG">UG (asks Class XII and X)</option>
                      <option value="PG">PG (also asks the UG degree)</option>
                    </select>
                  </label>
                  <div className="flex gap-1 pb-1">
                    <button type="button" className={smallBtn} disabled={i === 0} onClick={() => setEdit(move(edit, i, -1))}>Up</button>
                    <button type="button" className={smallBtn} disabled={i === edit.length - 1} onClick={() => setEdit(move(edit, i, 1))}>Down</button>
                    <button type="button" className={`${smallBtn} text-red-700 border-red-300`} onClick={() => setEdit(edit.filter((_, n) => n !== i))}>Remove</button>
                  </div>
                </div>
                <div className="text-sm font-medium text-slate-800">Specialisations</div>
                <ListEditor items={p.specialisations} onChange={(specialisations) => setP({ specialisations })} addLabel="Add specialisation" rows={1} />
              </fieldset>
            )
          })}
          <button type="button" className="self-start text-sm border border-slate-400 rounded-md px-3 py-1.5 bg-white hover:bg-slate-50"
            onClick={() => setEdit([...edit, { name: '', level: 'UG', specialisations: [''] }])}>+ Add programme</button>
        </div>
      )
    case 'suggestions':
      return (
        <div className="grid gap-3 md:grid-cols-2">
          {['colleges', 'universities'].map((k) => (
            <label key={k} className="flex flex-col gap-1 text-sm font-medium text-slate-800">
              {k === 'colleges' ? 'Colleges' : 'Universities'} (one per line)
              <textarea className={field} rows={8} value={edit[k]} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} />
            </label>
          ))}
        </div>
      )
    default:
      return null
  }
}

function Section({ def, value, meta, onSaved, onDirtyChange, onSessionExpired, registerRetry }) {
  const [edit, setEdit] = useState(() => toEdit(def.key, value))
  const baseline = useRef(JSON.stringify(toEdit(def.key, value)))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const dirty = JSON.stringify(edit) !== baseline.current

  useEffect(() => onDirtyChange(def.key, dirty), [def.key, dirty, onDirtyChange])

  const accept = (data) => {
    const fresh = toEdit(def.key, data.content[def.key])
    baseline.current = JSON.stringify(fresh)
    setEdit(fresh)
    onSaved(data)
  }

  async function run(action) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const res = await action()
      accept(res.data.data)
      setNotice('Saved. Visitors see it within a minute.')
    } catch (err) {
      if (err?.response?.status === 401) {
        // Keep the edits: sign in over the page, then run the same action again.
        registerRetry(() => run(action))
        onSessionExpired()
      } else {
        setError(errorMessage(err))
      }
    } finally {
      setBusy(false)
    }
  }

  const save = () => run(() => adminContentApi.save(def.key, fromEdit(def.key, edit)))
  const reset = () => {
    if (!window.confirm(`Replace "${def.title}" with the default content? Your current text for this section will be lost.`)) return
    run(() => adminContentApi.reset(def.key))
  }

  return (
    <section aria-labelledby={`sec-${def.key}`} className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col gap-4">
      <div>
        <h2 id={`sec-${def.key}`} className="text-lg font-semibold text-slate-900">{def.title}</h2>
        <p className="text-sm text-slate-600 mt-0.5">{def.help}</p>
        <p className="text-xs text-slate-500 mt-1">{meta ? `Last changed ${formatDateTime(meta.updated_at)}` : 'Using the default content'}</p>
      </div>
      <SectionBody sectionKey={def.key} edit={edit} setEdit={(v) => { setNotice(''); setEdit(v) }} />
      {error && <p role="alert" className="text-sm font-medium text-red-700">{error}</p>}
      {notice && <p role="status" className="text-sm font-medium text-green-700">{notice}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={save} disabled={busy || !dirty}
          className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700 disabled:opacity-40">
          {busy ? 'Saving…' : 'Save'}
        </button>
        <button type="button" onClick={() => { setEdit(JSON.parse(baseline.current)); setError(''); setNotice('') }} disabled={busy || !dirty}
          className="px-3 py-2 rounded-md border border-slate-400 bg-white text-sm hover:bg-slate-50 disabled:opacity-40">
          Undo changes
        </button>
        {meta && (
          <button type="button" onClick={reset} disabled={busy}
            className="ml-auto px-3 py-2 rounded-md border border-slate-300 bg-white text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40">
            Reset to default
          </button>
        )}
        {dirty && <span className="text-xs text-amber-700">Unsaved changes</span>}
      </div>
    </section>
  )
}

export default function AdminContent() {
  const { status, admin, signOut, expire } = useAdminSession()
  const { reload: reloadSiteContent } = useContent()
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [dirtySections, setDirtySections] = useState({})
  const [reauth, setReauth] = useState(false) // false | 'save' (a save runs again after sign-in) | 'expired'
  const retry = useRef(null)

  useEffect(() => {
    if (status !== 'authed') return undefined
    let cancelled = false
    adminContentApi.get()
      .then((res) => !cancelled && setData(res.data.data))
      .catch((err) => {
        if (cancelled) return
        if (err?.response?.status === 401) expire()
        else setLoadError(errorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [status, expire])

  const anyDirty = Object.values(dirtySections).some(Boolean)
  useEffect(() => {
    if (!anyDirty) return undefined
    const warn = (e) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [anyDirty])

  // Writing guidelines makes no requests, so keep the session alive while someone is actively editing.
  useKeepAlive({ enabled: status === 'authed', onExpired: () => setReauth((r) => r || 'expired') })

  const onDirtyChange = useCallback(
    (key, dirty) => setDirtySections((d) => (d[key] === dirty ? d : { ...d, [key]: dirty })),
    [],
  )

  if (status === 'loading') return <p className="p-10 text-center text-slate-600">Checking your session…</p>
  if (status === 'anon') return <Navigate to="/admin/auth" replace />

  return (
    <div className="min-h-screen bg-slate-100">
      {reauth && (
        <ReauthDialog
          email={admin?.email}
          saving={reauth === 'save'}
          onSignedIn={() => {
            setReauth(false)
            const again = retry.current
            retry.current = null
            again?.()
          }}
          onCancel={() => {
            retry.current = null
            setReauth(false)
          }}
        />
      )}
      <header className="flex items-center gap-4 bg-slate-900 text-white px-6 py-3">
        <strong>AdmitFlow staff</strong>
        <nav aria-label="Admin sections" className="flex gap-4 text-sm ml-4">
          <Link to="/admin/dashboard" className="hover:underline">Applicants</Link>
          <Link to="/admin/stats" className="hover:underline">Statistics</Link>
          <Link to="/admin/tests" className="hover:underline">Tests</Link>
          <Link to="/admin/content" className="underline">Site content</Link>
        </nav>
        <span className="ml-auto text-slate-300 text-sm">{admin?.name}</span>
        <button onClick={signOut} className="text-sm border border-slate-500 rounded-md px-3 py-1 hover:bg-slate-700">Sign out</button>
      </header>

      <main className="max-w-4xl mx-auto p-6 flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Site content</h1>
          <p className="text-sm text-slate-600 mt-1">
            What applicants see about the institution. Each section saves on its own and appears on the site within a minute.{' '}
            <a href={BROCHURE_URL} target="_blank" rel="noopener noreferrer" className="underline">Open the brochure</a> (it is built from this content).
          </p>
        </div>
        {loadError && <p role="alert" className="text-red-700 font-medium">{loadError}</p>}
        {!data && !loadError && <p className="text-slate-600">Loading…</p>}
        {data && SECTIONS.map((def) => (
          <Section
            key={def.key}
            def={def}
            value={data.content[def.key]}
            meta={data.meta[def.key]}
            onSaved={(fresh) => {
              setData(fresh)
              reloadSiteContent(true) // so the rest of the app in this tab shows the change too
            }}
            onDirtyChange={onDirtyChange}
            onSessionExpired={() => setReauth('save')}
            registerRetry={(fn) => {
              retry.current = fn
            }}
          />
        ))}
      </main>
    </div>
  )
}
