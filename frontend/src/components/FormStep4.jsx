import FormStepNav from './FormStepNav'

// FR-6.6: Step 4 — Programme Preference (programme + dependent specialisation dropdown).
export default function FormStep4({ onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Programme Preference</h2>
      {/* TODO: programme + specialisation dropdowns */}
      <FormStepNav onNext={onNext} onBack={onBack} />
    </div>
  )
}
