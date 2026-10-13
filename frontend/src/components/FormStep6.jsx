import React, { useState, useRef } from 'react';
import { applicationApi } from '../api/client';

const ID_TYPES = ['Aadhaar', 'PAN', 'Voter ID'];
const LIMITS = { photo: 500 * 1024, signature: 200 * 1024, id_proof: 2 * 1024 * 1024 };
// Matches the formats the server accepts (backend/app/blueprints/application.py: IMAGE_FORMATS).
const IMAGE_ACCEPT = 'image/jpeg,image/png,image/webp,image/gif,image/bmp';
const LABELS = { photo: 'Photo', signature: 'Signature', id_proof: 'ID proof' };

const inputCls = 'mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2';
const fileCls =
  'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100';

function FileButton({ accept, onChange, hasFile }) {
  return (
    <label className="mt-1 inline-block cursor-pointer px-4 py-2 rounded bg-blue-50 text-blue-700 text-sm hover:bg-blue-100">
      {hasFile ? 'Replace file' : 'Choose file'}
      <input type="file" accept={accept} onChange={onChange} className="hidden" />
    </label>
  );
}

export default function FormStep6({
  applicationId,
  initialData = {},
  onNext,
  onBack,
  onAutoSave,
  onDocumentUploaded,
}) {
  const saved = initialData || {};
  const [photo, setPhoto] = useState(saved.photo_url || null);
  const [signature, setSignature] = useState(saved.signature_url || null);
  const [idProof, setIdProof] = useState(saved.id_proof_url || null);
  const [idType, setIdType] = useState(saved.id_proof_type || '');
  const [uploading, setUploading] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const ref = useRef({ photo, signature, idProof, idType });

  const buildPayload = () => ({
    photo_url: ref.current.photo,
    signature_url: ref.current.signature,
    id_proof_url: ref.current.idProof,
    id_proof_type: ref.current.idType,
  });

  const handleFileUpload = async (e, docType) => {
    const input = e.target;
    const file = input.files && input.files[0];
    if (!file) return;

    setError('');
    if (file.size > LIMITS[docType]) {
      setError(`${LABELS[docType]} is too large. Maximum size is ${Math.round(LIMITS[docType] / 1024)} KB.`);
      input.value = '';
      return;
    }

    setUploading(docType);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await applicationApi.uploadDocument(applicationId, docType, formData);
      if (res.data?.success) {
        const objectName = res.data.data.object_name;
        if (docType === 'photo') { ref.current.photo = objectName; setPhoto(objectName); }
        if (docType === 'signature') { ref.current.signature = objectName; setSignature(objectName); }
        if (docType === 'id_proof') { ref.current.idProof = objectName; setIdProof(objectName); }
        if (onDocumentUploaded) onDocumentUploaded(docType, objectName);
        if (onAutoSave) onAutoSave(buildPayload());
      } else {
        setError(res.data?.error || `Failed to upload ${LABELS[docType]}`);
        input.value = '';
      }
    } catch (err) {
      setError(err.response?.data?.error || `Upload failed for ${LABELS[docType]}`);
      input.value = '';
    } finally {
      setUploading('');
    }
  };

  const handleIdType = (e) => {
    const v = e.target.value;
    ref.current.idType = v;
    setIdType(v);
    if (onAutoSave) onAutoSave(buildPayload());
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = {};
    if (!photo) errs.photo = 'Photo is required';
    if (!signature) errs.signature = 'Signature is required';
    if (!idType) errs.id_type = 'Select the ID proof type';
    if (!idProof) errs.id_proof = 'ID proof is required';
    setFieldErrors(errs);
    if (Object.keys(errs).length > 0) {
      setError('Please complete all required items.');
      return;
    }
    setError('');
    onNext(buildPayload());
  };

  const Err = ({ k }) => (fieldErrors[k] ? <p className="text-xs text-red-600 mt-1">{fieldErrors[k]}</p> : null);

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Step 6: Document Uploads</h2>

      {error && <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">{error}</div>}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Applicant Photo * (JPEG or PNG, 150x200 to 600x800 px, under 500 KB)
          </label>
          <FileButton accept={IMAGE_ACCEPT} hasFile={!!photo} onChange={(e) => handleFileUpload(e, 'photo')} />
          {uploading === 'photo' && <span className="text-xs text-blue-500">Uploading photo...</span>}
          {photo && <span className="text-xs text-green-600 block mt-1">✓ Photo uploaded ({photo.split('/').pop()})</span>}
          <Err k="photo" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Signature * (JPEG or PNG, under 200 KB)</label>
          <FileButton accept={IMAGE_ACCEPT} hasFile={!!signature} onChange={(e) => handleFileUpload(e, 'signature')} />
          {uploading === 'signature' && <span className="text-xs text-blue-500">Uploading signature...</span>}
          {signature && <span className="text-xs text-green-600 block mt-1">✓ Signature uploaded ({signature.split('/').pop()})</span>}
          <Err k="signature" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">ID Proof Type *</label>
          <select value={idType} onChange={handleIdType} className={inputCls}>
            <option value="">Select ID proof type</option>
            {ID_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <Err k="id_type" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">ID Proof Photocopy * (PDF, under 2 MB)</label>
          <FileButton accept="application/pdf" hasFile={!!idProof} onChange={(e) => handleFileUpload(e, 'id_proof')} />
          {uploading === 'id_proof' && <span className="text-xs text-blue-500">Uploading ID proof...</span>}
          {idProof && <span className="text-xs text-green-600 block mt-1">✓ ID proof uploaded ({idProof.split('/').pop()})</span>}
          <Err k="id_proof" />
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <button
          type="button"
          onClick={() => onBack && onBack(buildPayload())}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Back
        </button>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Save & Proceed to Payment
        </button>
      </div>
    </form>
  );
}
