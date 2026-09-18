// FR-6.8: document upload control. Server performs the real MIME/size/dimension validation;
// this component only offers a lightweight client-side pre-check.
export default function UploadBox({ label, accept, maxSizeBytes, onSelect }) {
  const handleChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (maxSizeBytes && file.size > maxSizeBytes) {
      alert(`${label} exceeds the maximum allowed size.`)
      return
    }
    onSelect(file)
  }

  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-medium">{label}</span>
      <input type="file" accept={accept} onChange={handleChange} className="border rounded p-2" />
    </label>
  )
}
