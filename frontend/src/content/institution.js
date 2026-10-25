// The institution's content (name, contact, dates, guidelines, eligibility, documents, fee, college
// suggestions, programmes) is no longer built into the website: admins edit it in the portal
// (/admin/content), the server stores it, and the app loads it at start-up (context/ContentContext.jsx).
// The starting values for a new deployment are in backend/app/content_defaults.json.
//
// What stays here is the academic-project notice, which is deliberately NOT editable: whether it is
// shown is a per-deployment server setting (ADMITFLOW_DEMO_MODE), so no admin can remove it from the
// public demo.

export const DEMO_NOTICE =
  'Academic project, for demonstration only. This is not the admissions portal of any real college: ' +
  'no admissions are offered, and payments run in test mode (no real money is charged).'
