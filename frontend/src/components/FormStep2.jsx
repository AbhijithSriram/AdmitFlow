import React, { useEffect } from 'react'

export default function FormStep2({ formData, onChange }) {
  useEffect(() => {
    if (formData.pincode && formData.pincode.length === 6) {
      fetch(`https://api.postalpincode.in/pincode/${formData.pincode}`)
        .then((res) => res.json())
        .then((data) => {
          if (data && data[0] && data[0].Status === 'Success') {
            const details = data[0].PostOffice[0]
            onChange({ target: { name: 'district', value: details.District } })
            onChange({ target: { name: 'state', value: details.State } })
          }
        })
        .catch(() => null)
    }
  }, [formData.pincode])

  return (
    <div className="space-y-4 max-w-2xl">
      <h2 className="text-xl font-bold text-gray-900">Address Details</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Address Line 1 *</label>
          <input
            type="text"
            name="address_line1"
            value={formData.address_line1 || ''}
            onChange={onChange}
            required
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="Street address, House No."
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Pincode *</label>
          <input
            type="text"
            name="pincode"
            maxLength={6}
            value={formData.pincode || ''}
            onChange={onChange}
            required
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="6-digit Pincode"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">District</label>
          <input
            type="text"
            name="district"
            value={formData.district || ''}
            onChange={onChange}
            className="w-full p-2 border border-gray-300 rounded-md bg-gray-50"
            placeholder="Auto-filled from pincode"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
          <input
            type="text"
            name="state"
            value={formData.state || ''}
            onChange={onChange}
            className="w-full p-2 border border-gray-300 rounded-md bg-gray-50"
            placeholder="Auto-filled from pincode"
          />
        </div>
      </div>
    </div>
  )
}