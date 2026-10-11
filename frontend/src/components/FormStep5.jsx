import React, { useState, useRef } from 'react';

const STATUSES = ['Not Written', 'Written - Results Awaited', 'Written - Results Out'];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

// TODO: confirm the registration number format with the SRD. Placeholder: 6-15 letters/digits.
const REG_RE = /^[A-Za-z0-9]{6,15}$/;

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';

// Result fields are included ONLY when status is "Written - Results Out" (FR-6.7).
function buildPayload(f) {
  const t = (v) => (typeof v === 'string' ? v.trim() : v);
  const p = { entrance_status: f.entrance_status };
  if (f.entrance_status === 'Written - Results Out') {
    p.result_year = t(f.result_year);
    p.result_month = f.result_month;
    p.registration_number = t(f.registration_number);
    p.score = t(f.score);
    p.paper_code = t(f.paper_code);
  }
  return p;
}

function validate(f) {
  const e = {};
  if (!f.entrance_status) {
    e.entrance_status = 'Please select an option';
    return e;
  }
  if (f.entrance_status !== 'Written - Results Out') return e; // hidden fields are not validated

  const now = new Date();
  const year = String(f.result_year || '').trim();
  if (!year) {
    e.result_year = 'Year is required';
  } else if (!/^\d{4}$/.test(year) || +year < 2000 || +year > now.getFullYear()) {
    e.result_year = 'Enter a valid 4-digit year (not in the future)';
  }
  if (!f.result_month) {
    e.result_month = 'Month is required';
  } else if (/^\d{4}$/.test(year) && +year === now.getFullYear() && MONTHS.indexOf(f.result_month) > now.getMonth()) {
    e.result_month = 'Result month cannot be in the future';
  }

  const reg = String(f.registration_number || '').trim();
  if (!reg) e.registration_number = 'Registration number is required';
  else if (!REG_RE.test(reg)) e.registration_number = 'Registration number must be 6-15 letters or digits';

  const score = String(f.score || '').trim();
  if (!score) e.score = 'Score is required';
  else if (!/^\d{1,6}(\.\d{1,2})?$/.test(score) || !(Number(score) > 0)) e.score = 'Enter a valid score above 0';

  if (!String(f.paper_code || '').trim()) e.paper_code = 'Paper / subject code is required';
  return e;
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

export default function FormStep5({ initialData = {}, onNext, onBack, onAutoSave }) {
  const saved = initialData || {};
  const initial = {
    entrance_status: saved.entrance_status ?? '',
    result_year: saved.result_year ?? '',
    result_month: saved.result_month ?? '',
    registration_number: saved.registration_number ?? '',
    score: saved.score ?? '',
    paper_code: saved.paper_code ?? '',
  };
  const [f, setF] = useState(initial);
  const fRef = useRef(initial);
  const [errors, setErrors] = useState({});

  const update = (patch, save = false) => {
    const next = { ...fRef.current, ...patch };
    fRef.current = next;
    setF(next);
    if (save && onAutoSave) onAutoSave(buildPayload(next));
  };
  const text = (name) => ({
    value: f[name],
    onChange: (e) => update({ [name]: e.target.value }),
    onBlur: () => onAutoSave && onAutoSave(buildPayload(fRef.current)),
    className: inputCls,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate(f);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onNext(buildPayload(f));
  };

  const resultsOut = f.entrance_status === 'Written - Results Out';

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Step 5: Entrance Exam Details</h2>

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">
          Please fix the highlighted fields.
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700">Entrance Exam Status *</label>
        <div className="mt-2 space-y-2">
          {STATUSES.map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="radio"
                name="entrance_status"
                value={s}
                checked={f.entrance_status === s}
                onChange={() => update({ entrance_status: s }, true)}
              />
              {s}
            </label>
          ))}
        </div>
        {errors.entrance_status && <p className="text-xs text-red-600 mt-1">{errors.entrance_status}</p>}
      </div>

      {resultsOut && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Year of Exam Result" required error={errors.result_year}>
            <input type="text" inputMode="numeric" maxLength={4} {...text('result_year')} />
          </Field>
          <Field label="Month of Exam Result" required error={errors.result_month}>
            <select
              value={f.result_month}
              onChange={(e) => update({ result_month: e.target.value }, true)}
              className={inputCls}
            >
              <option value="">Select Month</option>
              {MONTHS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </Field>
          <Field label="Registration Number" required error={errors.registration_number}>
            <input type="text" {...text('registration_number')} />
          </Field>
          <Field label="Score" required error={errors.score}>
            <input type="text" inputMode="decimal" {...text('score')} />
          </Field>
          <Field label="Paper / Subject Code" required error={errors.paper_code}>
            <input type="text" {...text('paper_code')} />
          </Field>
        </div>
      )}

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
