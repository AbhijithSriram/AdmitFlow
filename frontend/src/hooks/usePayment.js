import { useCallback, useState } from 'react'
import { applicationApi } from '../api/client'

// FR-6.9: create a Razorpay order, open the checkout modal, and verify server-side on success.
export function usePayment() {
  const [status, setStatus] = useState('idle') // idle | creating | processing | success | failed

  const pay = useCallback(async () => {
    setStatus('creating')
    const { data } = await applicationApi.createPaymentOrder()
    const order = data.data

    return new Promise((resolve, reject) => {
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID,
        amount: order.amount,
        currency: order.currency,
        order_id: order.id,
        handler: async (response) => {
          setStatus('processing')
          try {
            await applicationApi.confirmPayment(response)
            setStatus('success')
            resolve(response)
          } catch (error) {
            setStatus('failed')
            await applicationApi.paymentFailed(response)
            reject(error)
          }
        },
        modal: {
          ondismiss: async () => {
            setStatus('failed')
            await applicationApi.paymentFailed({ order_id: order.id, dismissed: true })
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
