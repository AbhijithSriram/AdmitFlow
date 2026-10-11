import { useEffect, useState } from 'react'
import { applicationApi } from '../api/client'

// Loads saved draft data for an application.
// draft is per-step: { "1": {...}, "2": {...} }; lastStep is the highest saved step (0 if none).
export function useFormRehydrate(appId) {
  const [state, setState] = useState({
    loading: false,
    loaded: false,
    error: '',
    draft: {},
    lastStep: 0,
    documents: {},
    status: null,
  })

  useEffect(() => {
    if (!appId) return
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: '' }))

    applicationApi
      .getDraft(appId)
      .then((res) => {
        if (cancelled) return
        const d = res.data?.data
        if (res.data?.success && d) {
          setState({
            loading: false,
            loaded: true,
            error: '',
            draft: d.draft || {},
            lastStep: d.last_step || 0,
            documents: d.documents || {},
            status: d.status || null,
          })
        } else {
          setState((s) => ({ ...s, loading: false, error: 'Could not load your saved data.' }))
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState((s) => ({ ...s, loading: false, error: 'Could not load your saved data.' }))
        }
      })

    return () => {
      cancelled = true
    }
  }, [appId])

  return state
}
