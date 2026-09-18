import FormStepNav from './FormStepNav'

// FR-6.3: Step 1 — Personal Details (pre-filled name/DOB/gender/email/phone, family, community, nationality).
export default function FormStep1({ onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Personal Details</h2>
      {/* TODO: personal detail fields */}
      <FormStepNav onNext={onNext} onBack={onBack} isFirstStep />
    </div>
  )
}
