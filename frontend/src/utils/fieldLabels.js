// Turns saved form fields into something a person can read. Used by the payment preview
// and the admin detail panel. Generic on purpose: the field names belong to Steps 1-6.

const WORDS = {
  ews: 'EWS', ug: 'UG', id: 'ID', cgpa: 'CGPA',
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
