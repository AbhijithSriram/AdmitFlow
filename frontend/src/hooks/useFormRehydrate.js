import { useEffect, useState } from 'react'
import { applicationApi } from '../api/client'

// FR-6.2: rehydrate all step data on page load / refresh so no progress is ever lost.
export function useFormRehydrate(applicationId) {
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!applicationId) {
      setLoading(false)
      return
    }

    let cancelled = false
    applicationApi
      .getDraft(applicationId)
      .then((response) => {
        if (!cancelled) setDraft(response.data.data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [applicationId])

  return { draft, loading }
}
