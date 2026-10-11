import { useRef, useCallback, useEffect, useState } from 'react'
import { applicationApi } from '../api/client'

// status: 'idle' | 'saving' | 'saved' | 'failed'
// Always pass the COMPLETE data object for the step: the backend replaces it.
export function useAutoSave({ appId, stepNum, delay = 500 } = {}) {
  const [status, setStatus] = useState('idle')
  const timerRef = useRef(null)
  const pendingRef = useRef(null) // { appId, stepNum, data }
  const queueRef = useRef(Promise.resolve())
  const seqRef = useRef(0)
  const mountedRef = useRef(true)
  const ctxRef = useRef({ appId, stepNum })
  ctxRef.current = { appId, stepNum }

  // Sends one save. Saves run one after another so they cannot overtake each other.
  const send = useCallback((job) => {
    const seq = ++seqRef.current
    if (mountedRef.current) setStatus('saving')
    const run = async () => {
      let ok = false
      try {
        const res = await applicationApi.saveDraftStep(job.appId, job.stepNum, job.data)
        ok = !!res?.data?.success
      } catch (err) {
        ok = false
      }
      if (mountedRef.current && seq === seqRef.current) {
        setStatus(ok ? 'saved' : 'failed')
      }
      return ok
    }
    const p = queueRef.current.then(run)
    queueRef.current = p
    return p
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      clearTimeout(timerRef.current)
      const job = pendingRef.current
      if (job) {
        pendingRef.current = null
        send(job) // flush anything still waiting on the debounce
      }
    }
  }, [send])

  // Debounced save (use from onBlur): fires `delay` ms after the last call.
  const triggerSave = useCallback(
    (data) => {
      const { appId: a, stepNum: s } = ctxRef.current
      if (!a || !s || !data) return
      pendingRef.current = { appId: a, stepNum: s, data }
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        const job = pendingRef.current
        pendingRef.current = null
        timerRef.current = null
        if (job) send(job)
      }, delay)
    },
    [send, delay]
  )

  // Immediate save (use for Next/Back). Resolves true on success, false on failure.
  const saveNow = useCallback(
    (data) => {
      clearTimeout(timerRef.current)
      timerRef.current = null
      pendingRef.current = null
      const { appId: a, stepNum: s } = ctxRef.current
      if (!a || !s || !data) return Promise.resolve(false)
      return send({ appId: a, stepNum: s, data })
    },
    [send]
  )

  return { status, triggerSave, saveNow }
}
