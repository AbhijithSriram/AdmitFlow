import React from 'react'

export default function FormStep4({ formData, onChange }) {
  return (
    <div className="space-y-4 max-w-2xl">
      <h2 className="text-xl font-bold text-gray-900">Programme Preference</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Degree Level *</label>
          <select
            name="degree_level"
            value={formData.degree_level || ''}
            onChange={onChange}
            required
            className="w-full p-2 border border-gray-300 rounded-md bg-white"
          >
            <option value="">Select Degree Level</option>
            <option value="Undergraduate">Undergraduate (B.Tech / B.Sc / B.A)</option>
            <option value="Postgraduate">Postgraduate (M.Tech / M.Sc / M.A)</option>
            <option value="Doctoral">Doctoral (Ph.D)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">First Choice Department *</label>
          <select
            name="primary_department"
            value={formData.primary_department || ''}
            onChange={onChange}
            required
            className="w-full p-2 border border-gray-300 rounded-md bg-white"
          >
            <option value="">Select Department</option>
            <option value="CSE">Computer Science & Engineering</option>
            <option value="ECE">Electronics & Communication Engineering</option>
            <option value="ME">Mechanical Engineering</option>
            <option value="CE">Civil Engineering</option>
          </select>
        </div>
      </div>
    </div>
  )
}