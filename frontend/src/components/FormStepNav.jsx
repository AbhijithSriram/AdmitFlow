import React from 'react'

export default function FormStepNav({ currentStep, setCurrentStep }) {
  const steps = [
    { id: 1, label: 'Personal' },
    { id: 2, label: 'Address' },
    { id: 3, label: 'Programme' },
    { id: 4, label: 'Academic' },
    { id: 5, label: 'Entrance' },
    { id: 6, label: 'Documents' },
  ]

  return (
    <div className="w-full mb-6 border-b pb-4">
      {/* STEP PROGRESS TRACKER ONLY — NO BACK/NEXT BUTTONS */}
      <div className="flex items-center justify-between">
        {steps.map((step) => {
          const isActive = currentStep === step.id
          const isCompleted = currentStep > step.id

          return (
            <div
              key={step.id}
              onClick={() => {
                // Allow clicking past steps to navigate back
                if (step.id < currentStep) {
                  setCurrentStep(step.id)
                }
              }}
              className={`flex items-center space-x-2 cursor-pointer ${
                step.id < currentStep ? 'cursor-pointer' : 'cursor-default'
              }`}
            >
              <div
                className={`w-8 h-8 flex items-center justify-center rounded-full font-semibold text-sm ${
                  isActive
                    ? 'bg-black text-white'
                    : isCompleted
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {step.id}
              </div>
              <span
                className={`text-sm hidden sm:inline ${
                  isActive ? 'font-bold text-black' : 'text-gray-500'
                }`}
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}