import { useEffect, useRef, useState } from 'react'
import { adminApi } from '../../api/client'
import { errorMessage } from './adminUtils'

// FR-7.3: the delete button stays disabled until the admin types DELETE.
export default function DeleteStudentModal({ student, onClose, onDeleted }) {
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && !busy && !result && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, result, onClose])

  async function confirm() {
    setBusy(true)
    setError('')
    try {
      const res = await adminApi.deleteStudent(student.id, typed)
      setResult(res.data.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="del-title" className="bg-white rounded-lg max-w-md w-full p-6">
        {!result ? (
          <>
            <h2 id="del-title" className="text-lg font-semibold text-slate-900">
              Permanently delete {student.name}?
            </h2>
            <p className="text-sm text-slate-700 mt-2">
              This removes <strong>{student.email}</strong>, their application, drafts, payment records and every uploaded
              file. It cannot be undone. The action is recorded in the audit log.
            </p>
            <label className="block text-sm font-medium text-slate-800 mt-4">
              Type <code className="bg-red-50 text-red-700 px-1 rounded">DELETE</code> to confirm
              <input
                ref={inputRef}
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                autoComplete="off"
                className="mt-1 w-full border border-slate-400 rounded-md px-3 py-2 font-normal focus:outline-2 focus:outline-red-600"
              />
            </label>
            {error && (
              <p role="alert" className="text-sm font-medium text-red-700 mt-3">
                {error}
              </p>
            )}
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={onClose} disabled={busy} className="px-4 py-2 rounded-md border border-slate-400 text-slate-800 hover:bg-slate-50 disabled:opacity-50">
                Cancel
              </button>
              <button
                onClick={confirm}
                disabled={typed !== 'DELETE' || busy}
                className="px-4 py-2 rounded-md bg-red-700 text-white font-medium hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy ? 'Deleting…' : 'Delete permanently'}
              </button>
            </div>
          </>
        ) : (
          <>
            <h2 id="del-title" className="text-lg font-semibold text-slate-900">
              Deleted
            </h2>
            <p className="text-sm text-slate-700 mt-2">
              <strong>Files removed:</strong> {result.files_removed.length || 'none'}
            </p>
            <p className="text-sm text-slate-700 mt-1">
              <strong>Records removed:</strong>{' '}
              {Object.entries(result.cascaded)
                .filter(([, n]) => n > 0)
                .map(([table, n]) => `${table} (${n})`)
                .join(', ') || 'none besides the student'}
            </p>
            <div className="flex justify-end mt-5">
              <button onClick={() => onDeleted(student.id)} className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700">
                Done
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
