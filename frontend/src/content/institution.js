// Institution content shared by the landing page, the application form and the info pages,
// so they can never disagree with each other. All values below are DEMO PLACEHOLDERS:
// replace them with the institution's real details in this one file.

export const INSTITUTION_NAME = 'AdmitFlow Institute'

// Keep in sync with APPLICATION_FEE_PAISE in backend/app/blueprints/payment.py (100000 paise).
export const APPLICATION_FEE_INR = 1000

// programme -> specialisations offered under it (Step 4 dropdowns and the landing page).
export const PROGRAMMES = {
  'B.Tech': ['CSE', 'IT', 'ECE', 'EEE', 'Mechanical', 'Civil'],
  'M.Tech': ['Computer Science', 'VLSI Design', 'Data Science', 'Structural Engineering'],
  MCA: ['General'],
  'M.Sc.': ['Computer Science', 'Mathematics', 'Physics', 'Data Science'],
}

export const KEY_DATES = [
  { label: 'Applications open', value: '1 January' },
  { label: 'Last date to apply', value: '31 March' },
  { label: 'Entrance test', value: '20 April' },
  { label: 'Results announced', value: '15 May' },
]

export const GUIDELINES = [
  'Please read these guidelines carefully before starting your application.',
  'All information you provide must be accurate and match your official documents.',
  'Your progress is saved automatically as you fill in each field.',
  'You will need a passport-size photograph and a signature (JPEG or PNG images) and an ID proof (PDF).',
  'Applications cannot be edited after payment is completed.',
  'Providing false information may lead to cancellation of your application.',
  'The application fee is non-refundable.',
  'Keep your registration details and receipts safe for future reference.',
  'By clicking "I Agree & Proceed" you confirm that you have read and accepted these guidelines.',
]

export const ELIGIBILITY = [
  'A completed or final-year undergraduate degree (B.E., B.Tech, B.Sc., BCA, MCA or M.Sc.) from a recognised university.',
  'Applicants awaiting results may apply and must submit proof of the result before admission.',
  'Applicants from outside India (NRI / OCI) must provide passport details.',
  'Reservation categories (General, OBC, BC, SC, ST) and EWS status are applied as per government norms.',
]

export const CONTACT = {
  email: 'admissions@example.edu',
  phone: '+91 00000 00000',
  address: 'Admissions Office, AdmitFlow Institute, Main Campus',
  hours: 'Monday to Friday, 9:30 am to 4:30 pm',
}
