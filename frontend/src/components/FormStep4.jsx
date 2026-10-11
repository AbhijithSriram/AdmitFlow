import React, { useState, useRef } from 'react';
import { PROGRAMMES } from '../content/institution';

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';

function buildPayload(f) {
  return { programme: f.programme, specialisation: f.specialisation };
}

function Field({ label, required, error, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {required && ' *'}
      </label>
      {children}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}

export default function FormStep4({ initialData = {}, onNext, onBack, onAutoSave }) {
  const saved = initialData || {};
  const initial = {
    programme: saved.programme ?? '',
    specialisation: saved.specialisation ?? '',
  };
  const [f, setF] = useState(initial);
  const fRef = useRef(initial);
  const [errors, setErrors] = useState({});

  const update = (patch) => {
    const next = { ...fRef.current, ...patch };
    fRef.current = next;
    setF(next);
    if (onAutoSave) onAutoSave(buildPayload(next));
  };

  const options = PROGRAMMES[f.programme] || [];

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = {};
    if (!f.programme) errs.programme = 'Programme is required';
    if (!f.specialisation || !options.includes(f.specialisation)) {
      errs.specialisation = 'Specialisation is required';
    }
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onNext(buildPayload(f));
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Step 4: Programme Preference</h2>

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">
          Please fix the highlighted fields.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Programme" required error={errors.programme}>
          <select
            value={f.programme}
            onChange={(e) => update({ programme: e.target.value, specialisation: '' })}
            className={inputCls}
          >
            <option value="">Select Programme</option>
            {Object.keys(PROGRAMMES).map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </Field>
        <Field label="Specialisation" required error={errors.specialisation}>
          <select
            value={options.includes(f.specialisation) ? f.specialisation : ''}
            onChange={(e) => update({ specialisation: e.target.value })}
            disabled={!f.programme}
            className={inputCls + (f.programme ? '' : ' bg-gray-100')}
          >
            <option value="">{f.programme ? 'Select Specialisation' : 'Select a programme first'}</option>
            {options.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </Field>
      </div>

      <div className="flex justify-between pt-4">
        <button
          type="button"
          onClick={() => onBack && onBack(buildPayload(fRef.current))}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Back
        </button>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Save & Next
        </button>
      </div>
    </form>
  );
}
