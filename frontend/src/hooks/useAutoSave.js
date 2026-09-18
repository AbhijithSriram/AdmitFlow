import { useCallback, useRef, useState } from 'react'
import { applicationApi } from '../api/client'

const DEBOUNCE_MS = 500

// FR-6.2: field-level auto-save on blur, debounced, with a visible save-status indicator.
export function useAutoSave(applicationId, stepNumber) {
  const [status, setStatus] = useState('idle') // idle | saving | saved | error
  const timeoutRef = useRef(null)

  const save = useCallback(
    (fieldData) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)

      timeoutRef.current = setTimeout(async () => {
        setStatus('saving')
        try {
          await applicationApi.saveDraftStep(applicationId, stepNumber, fieldData)
          setStatus('saved')
        } catch {
          setStatus('error')
        }
      }, DEBOUNCE_MS)
    },
    [applicationId, stepNumber],
  )

  const saveNow = useCallback(
    async (fieldData) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      setStatus('saving')
      try {
        await applicationApi.saveDraftStep(applicationId, stepNumber, fieldData)
        setStatus('saved')
      } catch {
        setStatus('error')
        throw new Error('Save failed')
      }
    },
    [applicationId, stepNumber],
  )

  return { status, save, saveNow }
}
