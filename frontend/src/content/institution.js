// Institution content shared by the landing page, the application form, the info pages and the
// brochure, so they can never disagree with each other.
//
// AdmitFlow is an ACADEMIC PROJECT running on a public address. "AdmitFlow Institute" is fictional:
// the content below is realistic (modelled on a real lateral-entry admissions portal the author built
// earlier) but names no real college, phone number or office, and every page carries DEMO_NOTICE, so
// nobody can mistake this site for a real college's admissions portal.

export const INSTITUTION_NAME = 'AdmitFlow Institute'

// Shown on every page (components/DemoNotice.jsx). Keep it short; the About page has the full text.
export const DEMO_NOTICE =
  'Academic project, for demonstration only. This is not the admissions portal of any real college: ' +
  'no admissions are offered, and payments run in test mode (no real money is charged).'

export const ABOUT = [
  'AdmitFlow is a student project built for a Full Stack Web Development course. It shows how a college ' +
    'admissions portal works end to end: registration with email verification, a multi-step application form ' +
    'that saves as you type, document uploads, online fee payment, a timed online aptitude test, and a staff ' +
    'portal with statistics and exports.',
  '"AdmitFlow Institute" is a fictional college. The programmes, dates, fees and rules on this site are ' +
    'realistic examples, not an offer of admission. Applying here does not lead to admission anywhere.',
  'Payments use the payment gateway’s test mode: no real money is charged, and receipts are not proof of any ' +
    'real payment. Please do not enter real card details.',
  'If you came here looking for a real college’s admissions, please contact that college directly.',
]

// Keep in sync with APPLICATION_FEE_PAISE in backend/app/blueprints/payment.py (100000 paise).
export const APPLICATION_FEE_INR = 1000

// programme -> specialisations offered under it (Step 3 dropdowns and the landing page).
// The names must match backend/migrations/006_seat_matrix.sql (the seat matrix).
export const PROGRAMMES = {
  'B.Tech': ['CSE', 'IT', 'ECE', 'EEE', 'Mechanical', 'Civil'],
  'M.Tech': ['Computer Science', 'VLSI Design', 'Data Science', 'Structural Engineering'],
  MCA: ['General'],
  'M.Sc.': ['Computer Science', 'Mathematics', 'Physics', 'Data Science'],
}

// Undergraduate entry: applicants give their Class XII and Class X details. Every other programme is
// postgraduate entry and also asks for the UG degree (Step 4 of the application form).
export const UG_PROGRAMMES = ['B.Tech']
export const isUgProgramme = (programme) => UG_PROGRAMMES.includes(programme)

// Suggestions for the College and University boxes in Step 4 (SRD FR-6.5): where an applicant may have
// studied before. Students can still type any other name. Keep names to letters and spaces so a picked
// suggestion is never altered by the text filters.
export const COLLEGES = [
  'College of Engineering Guindy',
  'Madras Institute of Technology',
  'PSG College of Technology',
  'Thiagarajar College of Engineering',
  'Coimbatore Institute of Technology',
  'Kumaraguru College of Technology',
  'Loyola College',
  'Presidency College',
  'Madras Christian College',
]

export const UNIVERSITIES = [
  'Anna University',
  'University of Madras',
  'Bharathiar University',
  'Bharathidasan University',
  'Madurai Kamaraj University',
  'Alagappa University',
  'Pondicherry University',
]

// An illustrative admissions cycle for the demo. Applications close before Class XII results come out,
// which is why B.Tech applicants can mark Class XII as "appearing / results awaited".
export const KEY_DATES = [
  { label: 'Applications open', value: '1 December 2026' },
  { label: 'Last date to apply', value: '31 March 2027, 11:59 pm IST' },
  { label: 'Online aptitude test (on this portal)', value: '12 to 16 April 2027' },
  { label: 'First shortlist', value: '30 April 2027' },
  { label: 'Results announced', value: '15 May 2027' },
]
export const DATES_NOTE = 'Illustrative dates for this academic demo.'

export const GUIDELINES = [
  'AdmitFlow is an academic project: applying here does not lead to admission anywhere, and payments run in ' +
    'test mode, so no real money is charged.',
  'Read the eligibility rules for your programme (Eligibility & Fee Structure) before you begin.',
  'Keep ready a recent passport-size photograph and your signature (JPEG or PNG), and an ID proof ' +
    '(Aadhaar, PAN or Voter ID) as a PDF.',
  'Fill in every detail exactly as it appears on your official documents. Original documents are verified ' +
    'at the time of admission.',
  'Your progress is saved automatically: you can log out and continue later from where you left off.',
  'The application is complete only when every step is filled in, the documents are uploaded and the fee is ' +
    'paid. Once the fee is paid, the application can no longer be edited.',
  `The application fee of ₹${APPLICATION_FEE_INR.toLocaleString('en-IN')} is non-refundable under any circumstances.`,
  'Submitting an application does not guarantee admission. Admission is on merit and subject to the eligibility rules.',
  'Paid applicants may be assigned a timed online aptitude test on this portal. It can be taken once, and the ' +
    'timer keeps running even if you close the page.',
  'If any information is found to be incorrect, the application or admission will be cancelled, even after the ' +
    'fee is paid.',
  'Keep your login details and the payment receipt for future reference.',
  'By clicking "I Agree & Proceed" you confirm that you have read and accepted these guidelines.',
]

export const ELIGIBILITY = [
  'B.Tech: a pass in Class XII (or equivalent) with Physics, Chemistry and Mathematics, and at least 60% ' +
    'aggregate in those three subjects (55% for SC/ST applicants). Students appearing for Class XII this year may apply.',
  'M.Tech: a B.E. or B.Tech in a related discipline with at least 60% marks, or a CGPA of 6.5 out of 10.',
  'MCA: a bachelor’s degree of at least three years with Mathematics at Class XII or degree level, with at ' +
    'least 50% marks.',
  'M.Sc.: a B.Sc. in the relevant subject with at least 55% marks.',
  'Final-year students may apply, and must produce their results before admission.',
  'Shortlisting is on merit: qualifying marks and the online aptitude test. Applicants at or above the test’s ' +
    'pass mark are shortlisted first; others may be considered later, subject to seats.',
  'Applicants from outside India (NRI / OCI) must provide passport details.',
  'Reservation categories (General, OBC, BC, SC, ST) and EWS status are applied as per government norms.',
]

// Originals checked at the time of admission (from the guidelines above).
export const DOCUMENTS_AT_ADMISSION = [
  'Class X and Class XII mark sheets',
  'Degree certificate and semester mark sheets (M.Tech, MCA and M.Sc.)',
  'Community certificate, if claiming a reservation category',
  'The ID proof uploaded with the application',
  'Transfer certificate from the last institution attended',
]

// There is no admissions office: the Contact page reaches the project team. Leave a field null to hide it.
export const CONTACT = {
  email: 'admitflow.noreply@gmail.com',
  phone: null,
  address: null,
  hours: null,
  note:
    'AdmitFlow is an academic project, so there is no admissions office or phone line. For questions about ' +
    'the project itself, write to the project team at the address above.',
}
