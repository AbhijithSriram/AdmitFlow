import React, { useState } from 'react';
import { stripFor, textError } from '../utils/textRules';

const STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
  'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh',
  'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands', 'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh',
  'Lakshadweep', 'Puducherry',
];
const COMMUNITIES = ['General', 'OBC', 'BC', 'SC', 'ST'];
const NATIONALITIES = ['Indian', 'NRI', 'OCI'];

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';
const readOnlyCls = inputCls + ' bg-gray-100 text-gray-600';

// Only visible fields go into the payload (hidden ones are excluded, FR-6.7 style).
function buildPayload(f) {
  const t = (v) => (typeof v === 'string' ? v.trim() : v);
  const p = {
    full_name: t(f.full_name),
    date_of_birth: f.date_of_birth,
    gender: f.gender,
    email: t(f.email),
    phone: t(f.phone),
    father_name: t(f.father_name),
    mother_name: t(f.mother_name),
    guardian_name: t(f.guardian_name),
    guardian_relationship: t(f.guardian_relationship),
    religion: t(f.religion),
    community: f.community,
    ews: f.ews,
    mother_tongue: t(f.mother_tongue),
    nationality: f.nationality,
  };
  if (f.nationality === 'Indian') {
    p.native_state = f.native_state;
  } else if (f.nationality === 'NRI' || f.nationality === 'OCI') {
    p.country = t(f.country);
    p.passport_number = t(f.passport_number);
  }
  return p;
}

function validate(f) {
  const e = {};
  const req = (k, msg) => {
    if (!String(f[k] ?? '').trim()) e[k] = msg;
  };
  req('father_name', "Father's name is required");
  req('mother_name', "Mother's name is required");
  req('religion', 'Religion is required');
  req('community', 'Community is required');
  req('mother_tongue', 'Mother tongue is required');
  req('nationality', 'Nationality is required');
  if (f.nationality === 'Indian') {
    req('native_state', 'Native state is required');
  } else if (f.nationality === 'NRI' || f.nationality === 'OCI') {
    req('country', 'Country is required');
    if (!String(f.passport_number || '').trim()) {
      e.passport_number = 'Passport number is required';
    } else if (!/^[A-Za-z0-9]{6,9}$/.test(f.passport_number.trim())) {
      e.passport_number = 'Passport number must be 6-9 letters or digits';
    }
  }
  if (String(f.guardian_relationship || '').trim() && !String(f.guardian_name || '').trim()) {
    e.guardian_name = 'Enter the guardian name or clear the relationship';
  }
  // Text boxes that must hold words, not numbers (a required-ness error above takes priority).
  const words = (k, kind, label) => {
    if (!e[k] && textError(kind, f[k], label)) e[k] = textError(kind, f[k], label);
  };
  words('father_name', 'person', "Father's name");
  words('mother_name', 'person', "Mother's name");
  words('guardian_name', 'person', 'Guardian name');
  words('guardian_relationship', 'person', 'Guardian relationship');
  words('religion', 'person', 'Religion');
  words('mother_tongue', 'person', 'Mother tongue');
  if (f.nationality === 'NRI' || f.nationality === 'OCI') words('country', 'place', 'Country');
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

export default function FormStep1({ initialData = {}, profile, onNext, onAutoSave }) {
  const saved = initialData || {};
  const [f, setF] = useState(() => ({
    full_name: saved.full_name ?? profile?.full_name ?? '',
    date_of_birth: saved.date_of_birth ?? profile?.date_of_birth ?? '',
    gender: saved.gender ?? profile?.gender ?? '',
    email: saved.email ?? profile?.email ?? '',
    phone: saved.phone ?? profile?.phone ?? '',
    father_name: saved.father_name ?? '',
    mother_name: saved.mother_name ?? '',
    guardian_name: saved.guardian_name ?? '',
    guardian_relationship: saved.guardian_relationship ?? '',
    religion: saved.religion ?? '',
    community: saved.community ?? '',
    ews: saved.ews ?? 'No',
    mother_tongue: saved.mother_tongue ?? '',
    nationality: saved.nationality ?? '',
    native_state: saved.native_state ?? '',
    country: saved.country ?? '',
    passport_number: saved.passport_number ?? '',
  }));
  const [errors, setErrors] = useState({});

  // saveNow=true for dropdowns/radios: save immediately with the new value.
  const set = (name, value, saveNow = false) => {
    const next = { ...f, [name]: value };
    setF(next);
    if (saveNow && onAutoSave) onAutoSave(buildPayload(next));
  };
  // `kind` (see utils/textRules.js) drops characters the box does not accept as they are typed.
  const text = (name, kind) => ({
    value: f[name],
    onChange: (e) => set(name, kind ? stripFor(kind, e.target.value) : e.target.value),
    onBlur: () => onAutoSave && onAutoSave(buildPayload(f)),
    className: inputCls,
  });
  const select = (name) => ({
    value: f[name],
    onChange: (e) => set(name, e.target.value, true),
    className: inputCls,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate(f);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onNext(buildPayload(f));
  };

  const isForeign = f.nationality === 'NRI' || f.nationality === 'OCI';

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Step 1: Personal Details</h2>

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">
          Please fix the highlighted fields.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Full Name">
          <input type="text" value={f.full_name} readOnly className={readOnlyCls} />
        </Field>
        <Field label="Date of Birth">
          <input type="text" value={f.date_of_birth} readOnly className={readOnlyCls} />
        </Field>
        <Field label="Gender">
          <input type="text" value={f.gender} readOnly className={readOnlyCls} />
        </Field>
        <Field label="Email">
          <input type="text" value={f.email} readOnly className={readOnlyCls} />
        </Field>
        <Field label="Phone">
          <input type="text" value={f.phone} readOnly className={readOnlyCls} />
        </Field>
        <div className="hidden md:block" />

        <Field label="Father's Name" required error={errors.father_name}>
          <input type="text" {...text('father_name', 'person')} />
        </Field>
        <Field label="Mother's Name" required error={errors.mother_name}>
          <input type="text" {...text('mother_name', 'person')} />
        </Field>
        <Field label="Guardian Name (optional)" error={errors.guardian_name}>
          <input type="text" {...text('guardian_name', 'person')} />
        </Field>
        <Field label="Guardian Relationship (optional)">
          <input type="text" {...text('guardian_relationship', 'person')} />
        </Field>

        <Field label="Religion" required error={errors.religion}>
          <input type="text" {...text('religion', 'person')} />
        </Field>
        <Field label="Community" required error={errors.community}>
          <select {...select('community')}>
            <option value="">Select Community</option>
            {COMMUNITIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field label="EWS" required>
          <div className="mt-2 flex gap-6">
            {['Yes', 'No'].map((v) => (
              <label key={v} className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="ews"
                  value={v}
                  checked={f.ews === v}
                  onChange={() => set('ews', v, true)}
                />
                {v}
              </label>
            ))}
          </div>
        </Field>
        <Field label="Mother Tongue" required error={errors.mother_tongue}>
          <input type="text" {...text('mother_tongue', 'person')} />
        </Field>

        <Field label="Nationality" required error={errors.nationality}>
          <select {...select('nationality')}>
            <option value="">Select Nationality</option>
            {NATIONALITIES.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </Field>

        {f.nationality === 'Indian' && (
          <Field label="Native State" required error={errors.native_state}>
            <select {...select('native_state')}>
              <option value="">Select State</option>
              {STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
        )}

        {isForeign && (
          <>
            <Field label="Country" required error={errors.country}>
              <input type="text" {...text('country', 'place')} />
            </Field>
            <Field label="Passport Number" required error={errors.passport_number}>
              <input type="text" {...text('passport_number')} />
            </Field>
          </>
        )}
      </div>

      <div className="flex justify-end pt-4">
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Save & Next
        </button>
      </div>
    </form>
  );
}
