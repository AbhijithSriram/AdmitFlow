// FR-6.2: step navigation fires a synchronous full-step save before advancing.
export default function FormStepNav({ onBack, onNext, saveStatus, isFirstStep }) {
  return (
    <div className="flex items-center justify-between mt-6">
      <span className="text-sm text-gray-500">
        {saveStatus === 'saving' && 'Saving…'}
        {saveStatus === 'saved' && 'Saved ✓'}
        {saveStatus === 'error' && 'Save failed'}
      </span>
      <div className="flex gap-2">
        {!isFirstStep && (
          <button type="button" onClick={onBack} className="px-4 py-2 rounded border">
            Back
          </button>
        )}
        <button type="button" onClick={onNext} className="px-4 py-2 rounded bg-black text-white">
          Next
        </button>
      </div>
    </div>
  )
}
