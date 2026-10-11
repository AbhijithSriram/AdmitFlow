import { useEffect, useState } from 'react'

export function useFormRehydrate(appId, setFormData) {
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!appId) return
    setLoading(true)
    fetch(`http://localhost:5000/api/app/draft/${appId}`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.success && data.draft) {
          setFormData((prev) => ({ ...prev, ...data.draft }))
        }
      })
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [appId, setFormData])

  return { loading }
}