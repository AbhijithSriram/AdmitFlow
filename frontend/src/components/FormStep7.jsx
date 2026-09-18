import { usePayment } from '../hooks/usePayment'

// FR-6.9: Step 7 — Preview & Payment (read-only summary, declaration, Razorpay checkout).
export default function FormStep7({ onBack }) {
  const { status, pay } = usePayment()

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Preview &amp; Payment</h2>
      {/* TODO: read-only summary of all steps + declaration checkbox */}
      <div className="flex items-center justify-between mt-6">
        <button type="button" onClick={onBack} className="px-4 py-2 rounded border">
          Back
        </button>
        <button type="button" onClick={pay} disabled={status === 'creating' || status === 'processing'} className="px-4 py-2 rounded bg-black text-white">
          Proceed to Pay
        </button>
      </div>
    </div>
  )
}
