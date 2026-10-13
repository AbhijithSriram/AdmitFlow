import React, { useState, useRef } from 'react';
import { isUgProgramme } from '../content/institution';
import { stripFor, textError } from '../utils/textRules';

// Step 4: Academic details. What is asked depends on the programme chosen in Step 3:
//   B.Tech (undergraduate entry)               -> Class XII and Class X
//   M.Tech / MCA / M.Sc. (postgraduate entry)  -> the UG degree, then Class XII and Class X

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
const BOARDS = ['CBSE', 'ICSE / ISC', 'State Board', 'Other'];
const XII_GROUPS = ['Physics, Chemistry, Mathematics', 'Physics, Chemistry, Biology', 'Other'];

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';

const UG_KEYS = [
  'ug_degree', 'ug_degree_other', 'ug_specialisation', 'status', 'college', 'university',
  'passing_month', 'passing_year', 'score_type', 'score',
];
const SCHOOL_KEYS = [
  'xii_status', 'xii_board', 'xii_school', 'xii_year', 'xii_group', 'xii_percentage',
  'x_board', 'x_school', 'x_year', 'x_percentage',
];

const PERCENT_RE = /^\d{1,3}(\.\d{1,2})?$/;
const thisYear = () => new Date().getFullYear();

// Only the fields that apply to this programme go into the payload (hidden ones are excluded,
// so answers for the other kind of programme never linger in the saved draft).
function buildPayload(f, ug) {
  const t = (v) => (typeof v === 'string' ? v.trim() : v);
  const p = {};
  if (!ug) {
    p.ug_degree = f.ug_degree;
    if (f.ug_degree === 'Other') p.ug_degree_other = t(f.ug_degree_other);
    p.ug_specialisation = t(f.ug_specialisation);
    p.status = f.status;
    p.college = t(f.college);
    p.university = t(f.university);
    p.passing_month = f.passing_month;
    p.passing_year = t(f.passing_year);
    if (f.status === 'Completed') {
      p.score_type = f.score_type;
      p.score = t(f.score);
    }
  } else {
    p.xii_status = f.xii_status;
  }
  p.xii_board = f.xii_board;
  p.xii_school = t(f.xii_school);
  p.xii_year = t(f.xii_year);
  p.xii_group = f.xii_group;
  // Undergraduate applicants write Class XII in the spring, before results: no marks to give yet.
  if (!ug || f.xii_status === 'Completed') p.xii_percentage = t(f.xii_percentage);
  p.x_board = f.x_board;
  p.x_school = t(f.x_school);
  p.x_year = t(f.x_year);
  p.x_percentage = t(f.x_percentage);
  return p;
}

function validate(f, ug) {
  const e = {};
  const req = (k, msg) => {
    if (!String(f[k] ?? '').trim()) e[k] = msg;
  };
  const words = (k, kind, label) => {
    if (!e[k] && textError(kind, f[k], label)) e[k] = textError(kind, f[k], label);
  };
  const now = new Date();
  const year = (k) => String(f[k] || '').trim();
  const yearOk = (k, max) => /^\d{4}$/.test(year(k)) && +year(k) >= 1990 && +year(k) <= max;
  const percent = (k, label) => {
    const raw = String(f[k] ?? '').trim();
    if (!raw) e[k] = `${label} is required`;
    else if (!PERCENT_RE.test(raw) || !(Number(raw) > 0) || Number(raw) > 100) {
      e[k] = `${label} must be a number above 0 and at most 100`;
    }
  };

  if (!ug) {
    req('ug_degree', 'UG degree is required');
    if (f.ug_degree === 'Other') req('ug_degree_other', 'Enter your degree name');
    req('ug_specialisation', 'Specialisation is required');
    req('status', 'Status is required');
    req('college', 'College is required');
    req('university', 'University is required');
    req('passing_month', 'Month is required');
    words('ug_degree_other', 'subject', 'Degree name');
    words('ug_specialisation', 'subject', 'Specialisation');
    words('college', 'org', 'College');
    words('university', 'org', 'University');

    if (!year('passing_year')) {
      e.passing_year = 'Year is required';
    } else if (!yearOk('passing_year', now.getFullYear() + 6)) {
      e.passing_year = 'Enter a valid 4-digit year';
    } else if (f.status === 'Completed' && f.passing_month) {
      const m = MONTHS.indexOf(f.passing_month);
      if (+year('passing_year') > now.getFullYear() || (+year('passing_year') === now.getFullYear() && m > now.getMonth())) {
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
        if (!PERCENT_RE.test(raw) || !(n > 0) || n > max) {
          e.score = `${f.score_type} must be a number above 0 and at most ${max}${f.score_type === 'CGPA' ? '.0' : ''}`;
        }
      }
    }
  }

  // Class XII
  const xiiDone = !ug || f.xii_status === 'Completed';
  if (ug) req('xii_status', 'Select whether Class XII is completed');
  req('xii_board', 'Board is required');
  req('xii_school', 'School is required');
  words('xii_school', 'org', 'School');
  req('xii_group', 'Subject group is required');
  if (!year('xii_year')) {
    e.xii_year = 'Year is required';
  } else if (!yearOk('xii_year', xiiDone ? thisYear() : thisYear() + 1)) {
    e.xii_year = xiiDone ? 'Enter a valid 4-digit year, not in the future' : 'Enter the year you will complete Class XII';
  }
  if (xiiDone) percent('xii_percentage', 'Class XII percentage');

  // Class X
  req('x_board', 'Board is required');
  req('x_school', 'School is required');
  words('x_school', 'org', 'School');
  if (!year('x_year')) {
    e.x_year = 'Year is required';
  } else if (!yearOk('x_year', thisYear())) {
    e.x_year = 'Enter a valid 4-digit year, not in the future';
  }
  percent('x_percentage', 'Class X percentage');

  if (!e.x_year && !e.xii_year && +year('xii_year') <= +year('x_year')) {
    e.xii_year = 'Class XII must be completed after Class X';
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

export default function FormStep4({ initialData = {}, programme, onNext, onBack, onAutoSave }) {
  const saved = initialData || {};
  const ug = isUgProgramme(programme);
  const initial = {};
  [...UG_KEYS, ...SCHOOL_KEYS].forEach((k) => {
    initial[k] = saved[k] ?? '';
  });

  const [f, setF] = useState(initial);
  const fRef = useRef(initial); // always the latest values
  const [errors, setErrors] = useState({});

  const update = (patch, save = false) => {
    const next = { ...fRef.current, ...patch };
    fRef.current = next;
    setF(next);
    if (save && onAutoSave) onAutoSave(buildPayload(next, ug));
  };
  // `kind` (see utils/textRules.js) drops characters the box does not accept as they are typed.
  const text = (name, kind) => ({
    value: f[name],
    onChange: (e) => update({ [name]: kind ? stripFor(kind, e.target.value) : e.target.value }),
    onBlur: () => onAutoSave && onAutoSave(buildPayload(fRef.current, ug)),
    className: inputCls,
  });
  const digits = (name, { maxLength, decimal = false } = {}) => ({
    value: f[name],
    inputMode: decimal ? 'decimal' : 'numeric',
    maxLength,
    onChange: (e) => update({ [name]: e.target.value.replace(decimal ? /[^\d.]/g : /\D/g, '') }),
    onBlur: () => onAutoSave && onAutoSave(buildPayload(fRef.current, ug)),
    className: inputCls,
  });
  const select = (name, extra = {}) => ({
    value: f[name],
    onChange: (e) => update({ [name]: e.target.value, ...extra }, true),
    className: inputCls,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate(f, ug);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onNext(buildPayload(f, ug));
  };

  if (!programme) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-800">Step 4: Academic Details</h2>
        <div className="p-3 bg-amber-50 text-amber-800 rounded-md text-sm">
          Choose your programme in Step 3 first. The academic details we ask for depend on it.
        </div>
        <button
          type="button"
          onClick={() => onBack && onBack()}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Back
        </button>
      </div>
    );
  }

  const xiiDone = !ug || f.xii_status === 'Completed';

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-8">
      <div>
        <h2 className="text-xl font-bold text-gray-800">Step 4: Academic Details</h2>
        <p className="text-sm text-gray-500 mt-1">
          {ug
            ? `For ${programme}: your Class XII and Class X details.`
            : `For ${programme}: your undergraduate degree, then Class XII and Class X.`}
        </p>
      </div>

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">
          Please fix the highlighted fields.
        </div>
      )}

      {!ug && (
        <section className="space-y-4">
          <h3 className="font-semibold text-gray-700">Undergraduate degree</h3>
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
                <input type="text" {...text('ug_degree_other', 'subject')} />
              </Field>
            ) : (
              <div className="hidden md:block" />
            )}

            <Field label="Specialisation" required error={errors.ug_specialisation}>
              <input type="text" list="specialisation-options" {...text('ug_specialisation', 'subject')} />
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
              <input type="text" {...text('college', 'org')} />
            </Field>
            <Field label="University" required error={errors.university}>
              <input type="text" {...text('university', 'org')} />
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
              <input type="text" {...digits('passing_year', { maxLength: 4 })} />
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
                  <input type="text" {...digits('score', { decimal: true })} />
                </Field>
              </>
            )}
          </div>
        </section>
      )}

      <section className="space-y-4">
        <h3 className="font-semibold text-gray-700">Class XII (Higher Secondary)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ug && (
            <Field label="Status" required error={errors.xii_status}>
              <select {...select('xii_status', { xii_percentage: '' })}>
                <option value="">Select Status</option>
                <option value="Completed">Completed</option>
                <option value="Results Awaited">Appearing / results awaited</option>
              </select>
            </Field>
          )}
          <Field label="Board" required error={errors.xii_board}>
            <select {...select('xii_board')}>
              <option value="">Select Board</option>
              {BOARDS.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </Field>
          <Field label="Subject Group" required error={errors.xii_group}>
            <select {...select('xii_group')}>
              <option value="">Select Subject Group</option>
              {XII_GROUPS.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </Field>
          <Field label="School" required error={errors.xii_school} className="md:col-span-2">
            <input type="text" {...text('xii_school', 'org')} />
          </Field>
          <Field label={xiiDone ? 'Year of Passing' : 'Expected Year of Passing'} required error={errors.xii_year}>
            <input type="text" {...digits('xii_year', { maxLength: 4 })} />
          </Field>
          {xiiDone && (
            <Field label="Percentage (max 100)" required error={errors.xii_percentage}>
              <input type="text" {...digits('xii_percentage', { decimal: true })} />
            </Field>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="font-semibold text-gray-700">Class X (Secondary)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Board" required error={errors.x_board}>
            <select {...select('x_board')}>
              <option value="">Select Board</option>
              {BOARDS.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </Field>
          <Field label="School" required error={errors.x_school}>
            <input type="text" {...text('x_school', 'org')} />
          </Field>
          <Field label="Year of Passing" required error={errors.x_year}>
            <input type="text" {...digits('x_year', { maxLength: 4 })} />
          </Field>
          <Field label="Percentage (max 100)" required error={errors.x_percentage}>
            <input type="text" {...digits('x_percentage', { decimal: true })} />
          </Field>
        </div>
      </section>

      <div className="flex justify-between pt-4">
        <button
          type="button"
          onClick={() => onBack && onBack(buildPayload(fRef.current, ug))}
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
