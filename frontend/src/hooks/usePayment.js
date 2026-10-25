import { useCallback, useState } from 'react'
import { applicationApi } from '../api/client'

// Telling the server about a failed attempt is best-effort: the student has already seen the failure,
// and a network error here must not turn into an unhandled promise rejection.
async function reportFailure(payload) {
  try {
    await applicationApi.paymentFailed(payload)
  } catch {
    // the server marks the application PAYMENT_PENDING on the next attempt anyway
  }
}

// FR-6.9: create a Razorpay order, open the checkout modal, and verify server-side on success.
export function usePayment() {
  const [status, setStatus] = useState('idle') // idle | creating | processing | success | failed

  const pay = useCallback(async () => {
    setStatus('creating')
    let order
    try {
      const { data } = await applicationApi.createPaymentOrder()
      order = data.data
    } catch (error) {
      // e.g. the payment gateway is unreachable: don't leave the button stuck on "Processing…"
      setStatus('failed')
      throw error
    }

    return new Promise((resolve, reject) => {
      // Once the checkout has reported a result, a later "dismissed" event (the modal closing
      // itself) must not be treated as a second, failed attempt.
      let settled = false

      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID,
        amount: order.amount,
        currency: order.currency,
        order_id: order.id,
        prefill: order.prefill,
        handler: async (response) => {
          settled = true
          setStatus('processing')
          try {
            await applicationApi.confirmPayment(response)
            setStatus('success')
            resolve(response)
          } catch (error) {
            setStatus('failed')
            await reportFailure(response)
            reject(error)
          }
        },
        modal: {
          ondismiss: async () => {
            if (settled) return
            settled = true
            setStatus('failed')
            await reportFailure({ order_id: order.id, dismissed: true })
            reject(new Error('Payment dismissed'))
          },
        },
      }

      const checkout = new window.Razorpay(options)
      checkout.open()
    })
  }, [])

  return { status, pay }
}
