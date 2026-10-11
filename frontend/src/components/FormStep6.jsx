import React, { useState } from 'react'

export default function FormStep6({ formData, onChange }) {
  const [uploading, setUploading] = useState({})
  const [errorMessages, setErrorMessages] = useState({})
  const [uploadedFiles, setUploadedFiles] = useState({
    photo: formData.photo_url ? 'Applicant Photo' : null,
    signature: formData.signature_url ? 'Signature' : null,
    id_proof: formData.id_proof_url ? 'ID Proof PDF' : null,
  })

  const handleFileUpload = async (e, docType) => {
    const file = e.target.files[0]
    if (!file) return

    setUploading((prev) => ({ ...prev, [docType]: true }))
    setErrorMessages((prev) => ({ ...prev, [docType]: '' }))

    const appId =
      sessionStorage.getItem('admitflow_app_id') ||
      localStorage.getItem('admitflow_app_id') ||
      '00000000-0000-0000-0000-000000000001'

    const payload = new FormData()
    payload.append('file', file)

    try {
      // Direct raw fetch without custom headers to bypass 403 preflight blocks
      const res = await fetch(`http://127.0.0.1:5000/api/upload/${appId}/${docType}`, {
        method: 'POST',
        body: payload,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data = await res.json()

      if (data.success) {
        setUploadedFiles((prev) => ({ ...prev, [docType]: file.name }))
        onChange({ target: { name: `${docType}_url`, value: data.url } })
      } else {
        setErrorMessages((prev) => ({ ...prev, [docType]: data.error || 'Upload failed' }))
      }
    } catch (err) {
      setErrorMessages((prev) => ({
        ...prev,
        [docType]: `Upload error (${err.message})`,
      }))
    } finally {
      setUploading((prev) => ({ ...prev, [docType]: false }))
    }
  }

  const handleRemoveFile = (docType) => {
    setUploadedFiles((prev) => ({ ...prev, [docType]: null }))
    onChange({ target: { name: `${docType}_url`, value: '' } })
  }

  const renderUploadBox = (docType, label, accept, limitText) => {
    const fileName = uploadedFiles[docType]
    const isUploading = uploading[docType]
    const errorMsg = errorMessages[docType]

    return (
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">{label} *</label>

        {fileName ? (
          <div className="flex items-center justify-between p-3 border border-green-300 bg-green-50 rounded-md">
            <div className="flex items-center space-x-2 overflow-hidden">
              <span className="text-green-600 font-bold">✓</span>
              <span className="text-sm font-medium text-gray-800 truncate">{fileName}</span>
            </div>
            <button
              type="button"
              onClick={() => handleRemoveFile(docType)}
              className="text-xs text-red-600 hover:text-red-800 font-semibold ml-4 whitespace-nowrap"
            >
              Change / Re-upload
            </button>
          </div>
        ) : (
          <div>
            <input
              type="file"
              accept={accept}
              onChange={(e) => handleFileUpload(e, docType)}
              disabled={isUploading}
              className="w-full p-2 border border-gray-300 rounded-md text-sm file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
            />
            <span className="text-xs text-gray-500 block mt-1">{limitText}</span>
          </div>
        )}

        {isUploading && <span className="text-xs text-blue-600 font-medium block">Uploading...</span>}
        {errorMsg && <span className="text-xs text-red-600 font-medium block">❌ {errorMsg}</span>}
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-xl font-bold text-gray-900">Document Uploads</h2>

      <div className="space-y-5">
        {renderUploadBox('photo', 'Applicant Photo', 'image/png, image/jpeg', 'PNG or JPEG, max 500KB')}
        {renderUploadBox('signature', 'Signature', 'image/png, image/jpeg', 'PNG or JPEG, max 200KB')}
        {renderUploadBox('id_proof', 'ID Proof', 'application/pdf', 'PDF document, max 2MB')}
      </div>
    </div>
  )
}