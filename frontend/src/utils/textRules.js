// Which characters each kind of text box accepts. The backend enforces the same rules
// (backend/app/services/field_rules.py): this file only gives the student quick feedback, so
// keep the two in step.
//
// \p{L} is any letter in any script and \p{M} the combining marks that Tamil, Hindi, Telugu and
// the other Indian scripts need, so names are not limited to A-Z.

// Names of people, religion, mother tongue, guardian relationship: letters only.
const PERSON = { allowed: /[\p{L}\p{M} .'’-]/u, valid: /^\p{L}[\p{L}\p{M} .'’-]*$/u, hint: 'letters only' }
// Districts, states and countries: letters, plus the & and ( ) in names like "Andaman & Nicobar Islands".
const PLACE = { allowed: /[\p{L}\p{M} .,&'’()-]/u, valid: /^\p{L}[\p{L}\p{M} .,&'’()-]*$/u, hint: 'letters only' }
// Towns: post-office names such as "Sector 5" do contain digits, and the pincode lookup fills them in.
const TOWN = { allowed: /[\p{L}\p{M}\p{N} .,&'’()/-]/u, valid: /^(?=.*\p{L})[\p{L}\p{M}\p{N} .,&'’()/-]+$/u, hint: 'letters and numbers only' }
// Degree name and specialisation: no digits.
const SUBJECT = { allowed: /[\p{L}\p{M} .,&'’()/-]/u, valid: /^\p{L}[\p{L}\p{M} .,&'’()/-]*$/u, hint: 'letters only' }
// College and university names can include numbers ("Anna University, Chennai - 25").
const ORG = TOWN

export const RULES = { person: PERSON, place: PLACE, town: TOWN, subject: SUBJECT, org: ORG }

// Drops the characters a box does not accept as the student types, so a stray digit never lands.
export function stripFor(kind, value) {
  const rule = RULES[kind]
  return Array.from(value).filter((ch) => rule.allowed.test(ch)).join('')
}

// Message for a filled-in value that breaks the rule, or '' if it is fine (or empty: required-ness
// is checked separately).
export function textError(kind, value, label) {
  const v = String(value ?? '').trim()
  if (!v) return ''
  const rule = RULES[kind]
  return rule.valid.test(v) ? '' : `${label} can contain ${rule.hint}`
}
