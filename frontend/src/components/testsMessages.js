// Messages for the student's aptitude test pages (SRD FR-10). Owner: Person 1.
// Plain JS (no JSX) so `npm test` can run them under node --test.

// The server answers 403 on every /api/student/tests route until the application is PAID.
export const NOT_PAID = 'Aptitude tests are available once your application fee has been paid.'

export const listErrorMessage = (status) =>
  status === 403 ? NOT_PAID : 'Could not load your aptitude tests. Try refreshing.'
