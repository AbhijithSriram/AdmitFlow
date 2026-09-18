import FormStepNav from './FormStepNav'

// FR-6.5: Step 3 — Academic Details (degree, course, college/university, score).
export default function FormStep3({ onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Academic Details</h2>
      {/* TODO: degree/course/college/score fields */}
      <FormStepNav onNext={onNext} onBack={onBack} />
    </div>
  )
}
