import { useState } from 'react'
import FormStep1 from '../components/FormStep1'
import FormStep2 from '../components/FormStep2'
import FormStep3 from '../components/FormStep3'
import FormStep4 from '../components/FormStep4'
import FormStep5 from '../components/FormStep5'
import FormStep6 from '../components/FormStep6'
import FormStep7 from '../components/FormStep7'

// FR-6: multi-step application form engine (guidelines + 7 steps), driven off one step index.
const STEPS = [FormStep1, FormStep2, FormStep3, FormStep4, FormStep5, FormStep6, FormStep7]

export default function ApplicationForm() {
  const [stepIndex, setStepIndex] = useState(0)
  const StepComponent = STEPS[stepIndex]

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <StepComponent
        onNext={() => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1))}
        onBack={() => setStepIndex((i) => Math.max(i - 1, 0))}
      />
    </div>
  )
}
