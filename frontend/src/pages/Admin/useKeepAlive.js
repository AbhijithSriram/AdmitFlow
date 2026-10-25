import { useEffect, useRef } from 'react'
import { adminApi } from '../../api/client'

const PING_EVERY_MS = 4 * 60 * 1000 // well inside the 30-minute idle timeout
const ACTIVE_WITHIN_MS = 5 * 60 * 1000

// While someone is really working on a long admin form, typing or clicking produces no requests, so
// the server would time the session out after 30 minutes and the next save would be refused. This
// pings the session every few minutes, but only if there was keyboard or pointer activity recently:
// a form left open and untouched still times out as before. If the session has ended anyway (expired
// before activity, or signed out in another tab), onExpired runs so the page can ask to sign in again
// instead of failing at save time.
export function useKeepAlive({ enabled = true, onExpired } = {}) {
  const lastActivity = useRef(Date.now())
  const onExpiredRef = useRef(onExpired)
  onExpiredRef.current = onExpired

  useEffect(() => {
    if (!enabled) return undefined
    const mark = () => {
      lastActivity.current = Date.now()
    }
    const events = ['keydown', 'input', 'pointerdown']
    events.forEach((e) => window.addEventListener(e, mark, { passive: true }))
    const timer = setInterval(async () => {
      if (Date.now() - lastActivity.current > ACTIVE_WITHIN_MS) return
      try {
        await adminApi.me()
      } catch (err) {
        if (err?.response?.status === 401) onExpiredRef.current?.()
      }
    }, PING_EVERY_MS)
    return () => {
      clearInterval(timer)
      events.forEach((e) => window.removeEventListener(e, mark))
    }
  }, [enabled])
}
