const LABELS = {
  NOT_STARTED: 'Not Started',
  IN_PROGRESS: 'In Progress',
  PAID: 'Submitted & Paid',
  PAYMENT_PENDING: 'Payment Pending',
}

const COLORS = {
  NOT_STARTED: 'bg-gray-200 text-gray-800',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-green-100 text-green-800',
  PAYMENT_PENDING: 'bg-red-100 text-red-800',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${COLORS[status] ?? COLORS.NOT_STARTED}`}>
      {LABELS[status] ?? status}
    </span>
  )
}
