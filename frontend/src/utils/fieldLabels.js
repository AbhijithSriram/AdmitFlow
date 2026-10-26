// Turns saved form fields into something a person can read. Used by the payment preview
// and the admin detail panel.
import FORM_FIELDS from './formFields.json' with { type: 'json' }

const WORDS = {
  ews: 'EWS', ug: 'UG', id: 'ID', cgpa: 'CGPA', x: 'Class X', xii: 'Class XII',
  comm: 'Communication', perm: 'Permanent', line1: 'line 1', line2: 'line 2',
}

// 'father_name' -> 'Father name', 'comm_line1' -> 'Communication line 1', 'ews' -> 'EWS'
export function humanize(label) {
  return String(label)
    .split(' / ')
    .map((part) => {
      const text = part
        .replace(/_/g, ' ')
        .split(/\s+/)
        .filter(Boolean)
        .map((word) => WORDS[word.toLowerCase()] ?? word)
        .join(' ')
      return text.charAt(0).toUpperCase() + text.slice(1)
    })
    .join(' / ')
}

// `*_url` entries are internal storage keys (applications/<id>/photo.png), not for people.
export const isInternalKey = (key) => key.endsWith('_url')

// [label, value] rows for one saved step, in the order the form asks them. The database (JSONB)
// returns a step's keys sorted, so the order and labels come from formFields.json; a field it does
// not list yet still shows, last. The backend's application PDF uses an identical copy of that file.
export function orderedRows(step, data) {
  const saved = Object.fromEntries(Object.entries(data ?? {}).filter(([key]) => !isInternalKey(key)))
  const known = FORM_FIELDS[step] ?? []
  const listed = new Set(known.map(([key]) => key))
  return [
    ...known.filter(([key]) => key in saved).map(([key, label]) => [label, saved[key]]),
    ...Object.entries(saved).filter(([key]) => !listed.has(key)).map(([key, value]) => [humanize(key), value]),
  ]
}

// Flattens one (possibly nested) object into "label -> value" rows, skipping internal keys.
export function flatten(data, prefix = '') {
  const rows = {}
  for (const [key, value] of Object.entries(data ?? {})) {
    if (isInternalKey(key)) continue
    const label = prefix ? `${prefix} / ${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(rows, flatten(value, label))
    } else {
      rows[label] = value
    }
  }
  return rows
}

export function display(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.join(', ')
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return String(value)
}
