import React, { useState, useRef } from 'react';

const DEGREES = ['B.E.', 'B.Tech', 'B.Sc.', 'BCA', 'MCA', 'M.Sc.', 'Other'];
const SPECIALISATIONS = [
  'Computer Science', 'Information Technology', 'Electronics and Communication',
  'Electrical and Electronics', 'Mechanical', 'Civil', 'Artificial Intelligence and Data Science',
  'Mathematics', 'Physics', 'Chemistry', 'Statistics', 'Computer Applications',
];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const STATUSES = ['Completed', 'Results Awaited'];
const SCORE_TYPES = ['CGPA', 'Percentage'];

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';

// Hidden fields are excluded from the payload (FR-6.7 style).
function buildPayload(f) {
  const t = (v) => (typeof v === 'string' ? v.trim() : v);
  const p = {
    ug_degree: f.ug_degree,
    ug_specialisation: t(f.ug_specialisation),
    status: f.status,
    college: t(f.college),
    university: t(f.university),
    passing_month: f.passing_month,
    passing_year: t(f.passing_year),
  };
  if (f.ug_degree === 'Other') p.ug_degree_other = t(f.ug_degree_other);
  if (f.status === 'Completed') {
    p.score_type = f.score_type;
    p.score = t(f.score);
  }
  return p;
}

function validate(f) {
  const e = {};
  const req = (k, msg) => {
    if (!String(f[k] ?? '').trim()) e[k] = msg;
  };
  req('ug_degree', 'UG degree is required');
  if (f.ug_degree === 'Other') req('ug_degree_other', 'Enter your degree name');
  req('ug_specialisation', 'Specialisation is required');
  req('status', 'Status is required');
  req('college', 'College is required');
  req('university', 'University is required');
  req('passing_month', 'Month is required');

  const now = new Date();
  const yearStr = String(f.passing_year || '').trim();
  if (!yearStr) {
    e.passing_year = 'Year is required';
  } else if (!/^\d{4}$/.test(yearStr) || +yearStr < 1990 || +yearStr > now.getFullYear() + 6) {
    e.passing_year = 'Enter a valid 4-digit year';
  } else if (f.status === 'Completed' && f.passing_month) {
    const m = MONTHS.indexOf(f.passing_month);
    if (+yearStr > now.getFullYear() || (+yearStr === now.getFullYear() && m > now.getMonth())) {
      e.passing_year = 'A completed degree cannot have a future passing date';
    }
  }

  if (f.status === 'Completed') {
    req('score_type', 'Score type is required');
    const raw = String(f.score ?? '').trim();
    if (!raw) {
      e.score = 'Score is required';
    } else if (f.score_type) {
      const max = f.score_type === 'CGPA' ? 10 : 100;
      const n = Number(raw);
      if (!/^\d{1,3}(\.\d{1,2})?$/.test(raw) || !(n > 0) || n > max) {
        e.score = `${f.score_type} must be a number above 0 and at most ${max}${f.score_type === 'CGPA' ? '.0' : ''}`;
      }
    }
  }
  return e;
}

function Field({ label, required, error, className = '', children }) {
  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {required && ' *'}
      </label>
      {children}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}

export default function FormStep3({ initialData = {}, onNext, onBack, onAutoSave }) {
  const saved = initialData || {};
  const initial = {
    ug_degree: saved.ug_degree ?? '',
    ug_degree_other: saved.ug_degree_other ?? '',
    ug_specialisation: saved.ug_specialisation ?? '',
    status: saved.status ?? '',
    college: saved.college ?? '',
    university: saved.university ?? '',
    passing_month: saved.passing_month ?? '',
    passing_year: saved.passing_year ?? '',
    score_type: saved.score_type ?? '',
    score: saved.score ?? '',
  };
  const [f, setF] = useState(initial);
  const fRef = useRef(initial); // always the latest values
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
  const select = (name, extra = {}) => ({
    value: f[name],
    onChange: (e) => update({ [name]: e.target.value, ...extra }, true),
    className: inputCls,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate(f);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onNext(buildPayload(f));
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Step 3: Academic Details</h2>

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">
          Please fix the highlighted fields.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="UG Degree" required error={errors.ug_degree}>
          <select {...select('ug_degree')}>
            <option value="">Select Degree</option>
            {DEGREES.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </Field>
        {f.ug_degree === 'Other' ? (
          <Field label="Degree Name" required error={errors.ug_degree_other}>
            <input type="text" {...text('ug_degree_other')} />
          </Field>
        ) : (
          <div className="hidden md:block" />
        )}

        <Field label="Specialisation" required error={errors.ug_specialisation}>
          <input type="text" list="specialisation-options" {...text('ug_specialisation')} />
          <datalist id="specialisation-options">
            {SPECIALISATIONS.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </Field>
        <Field label="Status" required error={errors.status}>
          <select {...select('status')}>
            <option value="">Select Status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </Field>

        <Field label="College" required error={errors.college}>
          <input type="text" {...text('college')} />
        </Field>
        <Field label="University" required error={errors.university}>
          <input type="text" {...text('university')} />
        </Field>

        <Field label="Month of Passing" required error={errors.passing_month}>
          <select {...select('passing_month')}>
            <option value="">Select Month</option>
            {MONTHS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </Field>
        <Field label="Year of Passing" required error={errors.passing_year}>
          <input type="text" inputMode="numeric" maxLength={4} {...text('passing_year')} />
        </Field>

        {f.status === 'Completed' && (
          <>
            <Field label="Score Type" required error={errors.score_type}>
              <select {...select('score_type', { score: '' })}>
                <option value="">Select Score Type</option>
                {SCORE_TYPES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </Field>
            <Field
              label={f.score_type === 'Percentage' ? 'Percentage (max 100)' : f.score_type === 'CGPA' ? 'CGPA (max 10.0)' : 'Score'}
              required
              error={errors.score}
            >
              <input type="text" inputMode="decimal" {...text('score')} />
            </Field>
          </>
        )}
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
