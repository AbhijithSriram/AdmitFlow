import { useRef, useCallback } from 'react'

export function useAutoSave({ appId, stepNum, data, delay = 1000 }) {
  const timeoutRef = useRef(null)

  const saveNow = useCallback(async () => {
    if (!appId || !stepNum) return
    try {
      await fetch(`http://localhost:5000/api/app/draft/${appId}/step/${stepNum}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
    } catch (err) {
      console.warn('Auto-save network error (mock fallback active)')
    }
  }, [appId, stepNum, data])

  const triggerSave = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => {
      saveNow()
    }, delay)
  }, [saveNow, delay])

  return { triggerSave, saveNow }
}