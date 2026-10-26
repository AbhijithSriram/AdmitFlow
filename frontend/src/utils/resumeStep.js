// Where "Continue Application" lands. `lastStep` is the highest saved step; `draft` is the saved
// form ({ "6": {...} }). A student who finished the uploads goes to the preview (Step 7) to pay,
// not back to Step 6.
const STEP_6_REQUIRED = ['photo_url', 'signature_url', 'id_proof_url', 'id_proof_type']

export function resumeStep(lastStep, draft) {
  const uploads = draft?.['6'] ?? {}
  if (lastStep >= 6 && STEP_6_REQUIRED.every((key) => uploads[key])) return 7
  return Math.min(6, Math.max(1, lastStep))
}
