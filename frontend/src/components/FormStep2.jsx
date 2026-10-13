import React, { useState, useRef } from 'react';
import { stripFor, textError } from '../utils/textRules';

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';
const readOnlyCls = inputCls + ' bg-gray-100 text-gray-600';
const PIN_RE = /^[1-9][0-9]{5}$/;
const FIELDS = ['line1', 'line2', 'town', 'pincode', 'district', 'state', 'country'];

// Communication fields mirror the permanent ones when "Same as Permanent" is ticked.
function buildPayload(f) {
  const t = (v) => (typeof v === 'string' ? v.trim() : v);
  const p = { same_as_permanent: !!f.same_as_permanent };
  FIELDS.forEach((k) => {
    p['perm_' + k] = t(f['perm_' + k]);
    p['comm_' + k] = t(f.same_as_permanent ? f['perm_' + k] : f['comm_' + k]);
  });
  return p;
}

function validate(f) {
  const e = {};
  const req = (k, msg) => {
    if (!String(f[k] ?? '').trim()) e[k] = msg;
  };
  req('perm_line1', 'Address line 1 is required');
  req('perm_town', 'Town / City is required');
  if (!String(f.perm_pincode).trim()) e.perm_pincode = 'Pincode is required';
  else if (f.perm_country.trim() === 'India' && !PIN_RE.test(f.perm_pincode.trim()))
    e.perm_pincode = 'Enter a valid 6-digit pincode';
  req('perm_district', 'District is required');
  req('perm_state', 'State is required');
  req('perm_country', 'Country is required');
  if (!f.same_as_permanent) {
    req('comm_line1', 'Address line 1 is required');
    req('comm_town', 'Town / City is required');
    req('comm_pincode', 'Pincode is required');
    req('comm_district', 'District is required');
    req('comm_state', 'State is required');
    req('comm_country', 'Country is required');
  }
  // Place names must hold words, not numbers (a required-ness error above takes priority).
  const words = (k, kind, label) => {
    if (!e[k] && textError(kind, f[k], label)) e[k] = textError(kind, f[k], label);
  };
  ['perm', ...(f.same_as_permanent ? [] : ['comm'])].forEach((pre) => {
    words(pre + '_town', 'town', 'Town / City');
    words(pre + '_district', 'place', 'District');
    words(pre + '_state', 'place', 'State');
    words(pre + '_country', 'place', 'Country');
  });
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

export default function FormStep2({ initialData = {}, onNext, onBack, onAutoSave }) {
  const saved = initialData || {};
  const initial = { same_as_permanent: saved.same_as_permanent ?? false };
  FIELDS.forEach((k) => {
    initial['perm_' + k] = saved['perm_' + k] ?? (k === 'country' ? 'India' : '');
    initial['comm_' + k] = saved['comm_' + k] ?? (k === 'country' ? 'India' : '');
  });

  const [f, setF] = useState(initial);
  const fRef = useRef(initial); // always the latest values (avoids stale closures)
  const [errors, setErrors] = useState({});
  const [lookup, setLookup] = useState({ loading: false, error: '', offices: [] });
  const lookupSeq = useRef(0);

  const update = (patch, save = false) => {
    const next = { ...fRef.current, ...patch };
    fRef.current = next;
    setF(next);
    if (save && onAutoSave) onAutoSave(buildPayload(next));
  };

  // `kind` (see utils/textRules.js) drops characters the box does not accept as they are typed.
  const text = (name, kind) => ({
    value: f[name],
    onChange: (e) => update({ [name]: kind ? stripFor(kind, e.target.value) : e.target.value }),
    onBlur: () => onAutoSave && onAutoSave(buildPayload(fRef.current)),
    className: inputCls,
  });

  const lookupPincode = async (pin) => {
    const seq = ++lookupSeq.current;
    setLookup({ loading: true, error: '', offices: [] });
    try {
      const res = await fetch(`https://api.postalpincode.in/pincode/${pin}`);
      if (!res.ok) throw new Error('bad response');
      const body = await res.json();
      if (seq !== lookupSeq.current) return; // a newer lookup replaced this one
      const entry = Array.isArray(body) ? body[0] : null;
      const offices = entry?.Status === 'Success' && Array.isArray(entry.PostOffice) ? entry.PostOffice : [];
      if (offices.length === 0) {
        setLookup({ loading: false, error: 'Pincode not found. Please check it or fill the fields manually.', offices: [] });
        return;
      }
      const patch = { perm_district: offices[0].District || '', perm_state: offices[0].State || '' };
      if (offices.length === 1) patch.perm_town = offices[0].Name || '';
      update(patch, true);
      setLookup({ loading: false, error: '', offices: offices.map((o) => o.Name) });
    } catch (err) {
      if (seq !== lookupSeq.current) return;
      setLookup({ loading: false, error: 'Could not look up the pincode. Please fill the fields manually.', offices: [] });
    }
  };

  const onPermPincode = (e) => {
    const v = e.target.value.replace(/\D/g, '').slice(0, 6);
    update({ perm_pincode: v });
    if (v.length === 6 && fRef.current.perm_country.trim() === 'India') {
      lookupPincode(v);
    } else {
      lookupSeq.current++;
      setLookup({ loading: false, error: '', offices: [] });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate(f);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onNext(buildPayload(f));
  };

  const same = f.same_as_permanent;
  // What the communication fields display: mirrored values when "same" is ticked.
  const commVal = (k) => (same ? f['perm_' + k] : f['comm_' + k]);
  const commProps = (k, kind) =>
    same
      ? { value: commVal(k), readOnly: true, className: readOnlyCls }
      : text('comm_' + k, kind);

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Step 2: Address</h2>

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">
          Please fix the highlighted fields.
        </div>
      )}

      <h3 className="text-lg font-semibold text-gray-700">Permanent Address</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Address Line 1" required error={errors.perm_line1} className="md:col-span-2">
          <input type="text" {...text('perm_line1')} />
        </Field>
        <Field label="Address Line 2 (optional)" className="md:col-span-2">
          <input type="text" {...text('perm_line2')} />
        </Field>
        <Field label="Pincode" required error={errors.perm_pincode}>
          <input
            type="text"
            inputMode="numeric"
            value={f.perm_pincode}
            onChange={onPermPincode}
            onBlur={() => onAutoSave && onAutoSave(buildPayload(fRef.current))}
            className={inputCls}
          />
          {lookup.loading && <p className="text-xs text-blue-600 mt-1">Looking up pincode…</p>}
          {lookup.error && <p className="text-xs text-red-600 mt-1">{lookup.error}</p>}
        </Field>
        <Field label="Town / City" required error={errors.perm_town}>
          <input type="text" list="perm-town-options" {...text('perm_town', 'town')} />
          <datalist id="perm-town-options">
            {lookup.offices.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
        </Field>
        <Field label="District" required error={errors.perm_district}>
          <input type="text" {...text('perm_district', 'place')} />
        </Field>
        <Field label="State" required error={errors.perm_state}>
          <input type="text" {...text('perm_state', 'place')} />
        </Field>
        <Field label="Country" required error={errors.perm_country}>
          <input type="text" {...text('perm_country', 'place')} />
        </Field>
      </div>

      <h3 className="text-lg font-semibold text-gray-700">Communication Address</h3>
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={same}
          onChange={(e) => update({ same_as_permanent: e.target.checked }, true)}
        />
        Same as Permanent
      </label>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Address Line 1" required error={errors.comm_line1} className="md:col-span-2">
          <input type="text" {...commProps('line1')} />
        </Field>
        <Field label="Address Line 2 (optional)" className="md:col-span-2">
          <input type="text" {...commProps('line2')} />
        </Field>
        <Field label="Pincode" required error={errors.comm_pincode}>
          <input type="text" {...commProps('pincode')} />
        </Field>
        <Field label="Town / City" required error={errors.comm_town}>
          <input type="text" {...commProps('town', 'town')} />
        </Field>
        <Field label="District" required error={errors.comm_district}>
          <input type="text" {...commProps('district', 'place')} />
        </Field>
        <Field label="State" required error={errors.comm_state}>
          <input type="text" {...commProps('state', 'place')} />
        </Field>
        <Field label="Country" required error={errors.comm_country}>
          <input type="text" {...commProps('country', 'place')} />
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
