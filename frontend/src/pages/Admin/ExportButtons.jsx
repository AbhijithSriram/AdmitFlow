import { useState } from 'react'
import { adminExportApi } from '../../api/client'

// FR-11: export the applicant list, with the filters currently applied to the table, as CSV or PDF.
// Owner: Person 3. Mounted once in AdminDashboard.jsx; this file holds all the export logic.

// The server names the file in Content-Disposition; fall back to a sensible name if it is missing.
function filenameFrom(response, fallback) {
  const header = response.headers?.['content-disposition'] ?? ''
  const match = /filename="([^"]+)"/.exec(header)
  return match ? match[1] : fallback
}

// Errors come back as a Blob too (responseType is 'blob'), so the JSON message has to be read out of it.
async function errorText(err) {
  try {
    const body = JSON.parse(await err.response.data.text())
    if (body?.error) return body.error
  } catch {
    // not JSON: fall through
  }
  return 'The export could not be downloaded. Please try again.'
}

export default function ExportButtons({ filters, onExpired }) {
  const [busy, setBusy] = useState(null) // null | 'csv' | 'pdf'
  const [error, setError] = useState('')

  const download = async (format) => {
    setBusy(format)
    setError('')
    // The table's page number is irrelevant: an export always contains every matching applicant.
    const { page: _page, ...params } = filters
    try {
      const response = await adminExportApi[format](params)
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filenameFrom(response, `admitflow-applicants.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      if (err?.response?.status === 401) onExpired?.()
      else setError(await errorText(err))
    } finally {
      setBusy(null)
    }
  }

  const button =
    'text-sm border border-slate-400 rounded-md px-3 py-2 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-wait'

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <span className="text-sm text-slate-700">Export these results:</span>
      <button type="button" onClick={() => download('csv')} disabled={busy !== null} className={button}>
        {busy === 'csv' ? 'Preparing CSV…' : 'CSV'}
      </button>
      <button type="button" onClick={() => download('pdf')} disabled={busy !== null} className={button}>
        {busy === 'pdf' ? 'Preparing PDF…' : 'PDF'}
      </button>
      {error && (
        <p role="alert" className="w-full text-sm font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
