import FormStepNav from './FormStepNav'

// FR-6.7: Step 5 — Entrance/Test Details (conditional fields shown only when results are out).
export default function FormStep5({ onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Entrance / Test Details</h2>
      {/* TODO: Not Written / Results Awaited / Results Out radio group + conditional fields */}
      <FormStepNav onNext={onNext} onBack={onBack} />
    </div>
  )
}
