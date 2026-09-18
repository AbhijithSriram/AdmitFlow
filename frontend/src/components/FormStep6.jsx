import UploadBox from './UploadBox'
import FormStepNav from './FormStepNav'

// FR-6.8: Step 6 — Document Uploads (photo, signature, ID proof).
export default function FormStep6({ onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Document Uploads</h2>
      <div className="flex flex-col gap-4">
        <UploadBox label="Applicant Photo (PNG, max 500KB)" accept="image/png" maxSizeBytes={500 * 1024} onSelect={() => {}} />
        <UploadBox label="Signature (PNG, max 200KB)" accept="image/png" maxSizeBytes={200 * 1024} onSelect={() => {}} />
        <UploadBox label="ID Proof (PDF, max 2MB)" accept="application/pdf" maxSizeBytes={2 * 1024 * 1024} onSelect={() => {}} />
      </div>
      <FormStepNav onNext={onNext} onBack={onBack} />
    </div>
  )
}
