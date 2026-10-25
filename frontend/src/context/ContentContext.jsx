import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { contentApi } from '../api/client'

// The site content (institution name, contact, dates, guidelines, eligibility, documents, fee,
// college suggestions, programmes) is edited by admins in the portal (/admin/content) and loaded
// once from GET /api/content when the app starts. Pages read it with useContent().
//
// If the content cannot be loaded, the app still works with EMPTY_CONTENT and a notice, so
// applicants can still log in and the error is visible rather than a blank page.

const EMPTY_CONTENT = {
  institution: { name: 'AdmitFlow', about: [] },
  contact: { email: null, phone: null, address: null, hours: null, note: null },
  dates: { items: [], note: null },
  guidelines: [],
  eligibility: [],
  documents: [],
  fee: { amount_inr: 0 },
  suggestions: { colleges: [], universities: [] },
  programmes: [],
  demo_mode: true,
}

const ContentContext = createContext(null)

export function ContentProvider({ children }) {
  const [state, setState] = useState({ status: 'loading', content: null })

  // reload() after an admin save asks for a fresh copy; the first load may use the cached one.
  const reload = useCallback(
    (fresh = false) =>
      contentApi
        .get({ fresh })
        .then((res) => setState({ status: 'ready', content: res.data.data }))
        .catch(() => setState((s) => ({ status: s.content ? 'ready' : 'error', content: s.content }))),
    [],
  )

  useEffect(() => {
    reload()
  }, [reload])

  const value = useMemo(() => ({ ...state, reload }), [state, reload])

  if (state.status === 'loading') {
    return <p className="p-10 text-center text-gray-500">Loading…</p>
  }
  return <ContentContext.Provider value={value}>{children}</ContentContext.Provider>
}

export function useContent() {
  const ctx = useContext(ContentContext)
  const content = ctx?.content ?? EMPTY_CONTENT
  return useMemo(() => {
    const feeText = `₹${Number(content.fee?.amount_inr ?? 0).toLocaleString('en-IN')}`
    const byName = Object.fromEntries((content.programmes ?? []).map((p) => [p.name, p]))
    return {
      content,
      loadFailed: ctx?.status === 'error',
      reload: ctx?.reload ?? (() => Promise.resolve()),
      feeText,
      // Admins may write {fee} in guidelines and other text; it always shows the current fee.
      fill: (text) => String(text ?? '').replaceAll('{fee}', feeText),
      programmeNames: (content.programmes ?? []).map((p) => p.name),
      specialisationsOf: (name) => byName[name]?.specialisations ?? [],
      // Undergraduate entry asks for Class XII and X; postgraduate also asks for the UG degree.
      isUgProgramme: (name) => byName[name]?.level === 'UG',
    }
  }, [content, ctx])
}
