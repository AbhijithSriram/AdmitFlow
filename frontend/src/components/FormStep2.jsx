import FormStepNav from './FormStepNav'

// FR-6.4: Step 2 — Address Details (pincode auto-fill via Indian Post Office API).
export default function FormStep2({ onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Address Details</h2>
      {/* TODO: permanent + communication address fields, pincode auto-fill */}
      <FormStepNav onNext={onNext} onBack={onBack} />
    </div>
  )
}
