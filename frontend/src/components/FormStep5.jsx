import React from 'react'

export default function FormStep5({ formData, onChange }) {
  return (
    <div className="space-y-4 max-w-2xl">
      <h2 className="text-xl font-bold text-gray-900">Entrance / Test Details</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Entrance Exam Name</label>
          <input
            type="text"
            name="exam_name"
            value={formData.exam_name || ''}
            onChange={onChange}
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="e.g. JEE Main / GATE / GRE"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Score / Rank</label>
          <input
            type="text"
            name="exam_score"
            value={formData.exam_score || ''}
            onChange={onChange}
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="e.g. 98.5 Percentile"
          />
        </div>
      </div>
    </div>
  )
}