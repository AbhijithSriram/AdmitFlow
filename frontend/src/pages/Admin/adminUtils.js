// Shared helpers for the admin pages.

/** Pull the human-readable message out of the {success:false, error} envelope. */
export function errorMessage(err) {
  return err?.response?.data?.error || 'Could not reach the server. Check your connection and try again.'
}

export const PAYMENT_LABELS = { NONE: 'No payment', PENDING: 'Pending', PAID: 'Paid' }

export const STAGE_OPTIONS = [
  ['NOT_STARTED', 'Not started'],
  ['IN_PROGRESS', 'In progress'],
  ['PAYMENT_PENDING', 'Payment pending'],
  ['PAID', 'Submitted & paid'],
]

// The API returns naive UTC timestamps without a zone suffix, so append Z before parsing.
export const formatDate = (iso) =>
  iso ? new Date(`${iso}Z`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export const formatDateTime = (iso) =>
  iso
    ? new Date(`${iso}Z`).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—'
