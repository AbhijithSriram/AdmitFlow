import React from 'react'

export default function FormStep3({ formData, onChange }) {
  return (
    <div className="space-y-4 max-w-2xl">
      <h2 className="text-xl font-bold text-gray-900">Academic Details</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">10th Percentage *</label>
          <input
            type="number"
            step="0.01"
            name="tenth_percentage"
            value={formData.tenth_percentage || ''}
            onChange={onChange}
            required
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="e.g. 88.5"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">12th Percentage *</label>
          <input
            type="number"
            step="0.01"
            name="twelfth_percentage"
            value={formData.twelfth_percentage || ''}
            onChange={onChange}
            required
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="e.g. 92.0"
          />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Undergraduate CGPA (Optional)</label>
          <input
            type="number"
            step="0.01"
            name="ug_cgpa"
            value={formData.ug_cgpa || ''}
            onChange={onChange}
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="e.g. 8.5"
          />
        </div>
      </div>
    </div>
  )
}