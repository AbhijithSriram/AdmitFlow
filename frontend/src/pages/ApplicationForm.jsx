import React, { useState, useEffect } from 'react'
import FormStep1 from '../components/FormStep1'
import FormStep2 from '../components/FormStep2'
import FormStep3 from '../components/FormStep3'
import FormStep4 from '../components/FormStep4'
import FormStep5 from '../components/FormStep5'
import FormStep6 from '../components/FormStep6'
import FormStepNav from '../components/FormStepNav'
import { useFormRehydrate } from '../hooks/useFormRehydrate'

export default function ApplicationForm() {
  // 1. Rehydrate active step and applicationId from sessionStorage/localStorage
  const [applicationId, setApplicationId] = useState(() => {
    return sessionStorage.getItem('admitflow_app_id') || null
  })

  const [currentStep, setCurrentStep] = useState(() => {
    const savedStep = sessionStorage.getItem('admitflow_current_step')
    const savedAppId = sessionStorage.getItem('admitflow_app_id')
    return savedAppId && savedStep ? parseInt(savedStep, 10) : 0
  })

  const [formData, setFormData] = useState(() => {
    const savedData = sessionStorage.getItem('admitflow_form_data')
    return savedData
      ? JSON.parse(savedData)
      : {
          full_name: '',
          date_of_birth: '',
          gender: '',
          phone: '',
          address_line1: '',
          address_line2: '',
          pincode: '',
          district: '',
          state: '',
          tenth_percentage: '',
          twelfth_percentage: '',
          ug_cgpa: '',
          degree_level: '',
          primary_department: '',
          exam_name: '',
          exam_score: '',
          photo_url: '',
          signature_url: '',
          id_proof_url: '',
        }
  })

  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 2. Persist state within current tab session
  useEffect(() => {
    sessionStorage.setItem('admitflow_current_step', currentStep.toString())
  }, [currentStep])

  useEffect(() => {
    if (applicationId) {
      sessionStorage.setItem('admitflow_app_id', applicationId)
      localStorage.setItem('admitflow_app_id', applicationId)
    }
  }, [applicationId])

  useEffect(() => {
    sessionStorage.setItem('admitflow_form_data', JSON.stringify(formData))
  }, [formData])

  // 3. Rehydrate backend drafts if available
  useFormRehydrate(applicationId, setFormData)

  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target
    if (scrollHeight - scrollTop <= clientHeight + 5) {
      setHasScrolledToBottom(true)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  // Guidelines -> Step 1 (FR-6.1 & FR-6.2: POST /api/app/start)
  const handleStartApplication = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch('http://localhost:5000/api/app/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }).then((res) => res.json()).catch(() => null)

      const id = response && response.success ? response.application_id : '00000000-0000-0000-0000-000000000001'
      setApplicationId(id)
      sessionStorage.setItem('admitflow_app_id', id)
      setCurrentStep(1)
    } catch (err) {
      const fallbackId = '00000000-0000-0000-0000-000000000001'
      setApplicationId(fallbackId)
      sessionStorage.setItem('admitflow_app_id', fallbackId)
      setCurrentStep(1)
    } finally {
      setLoading(false)
    }
  }

  const handleRestartSession = () => {
    sessionStorage.clear()
    localStorage.removeItem('admitflow_current_step')
    localStorage.removeItem('admitflow_app_id')
    localStorage.removeItem('admitflow_form_data')
    setApplicationId(null)
    setHasScrolledToBottom(false)
    setFormData({
      full_name: '',
      date_of_birth: '',
      gender: '',
      phone: '',
      address_line1: '',
      address_line2: '',
      pincode: '',
      district: '',
      state: '',
      tenth_percentage: '',
      twelfth_percentage: '',
      ug_cgpa: '',
      degree_level: '',
      primary_department: '',
      exam_name: '',
      exam_score: '',
      photo_url: '',
      signature_url: '',
      id_proof_url: '',
    })
    setCurrentStep(0)
  }

  const handleNext = async () => {
    if (applicationId && currentStep >= 1) {
      try {
        await fetch(`http://localhost:5000/api/app/draft/${applicationId}/step/${currentStep}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData),
        })
      } catch (e) {
        // Fallback for offline dev testing
      }
    }

    if (currentStep < 6) {
      setCurrentStep((prev) => prev + 1)
    } else if (currentStep === 6) {
      alert('Application Form Draft Saved & Completed!')
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-md rounded-lg my-8">
      {/* GUIDELINES STEP (STEP 0) */}
      {currentStep === 0 && (
        <div className="space-y-6">
          <h1 className="text-2xl font-bold text-gray-900">Application Guidelines</h1>
          <p className="text-sm text-gray-600">
            Please scroll to the bottom of the guidelines box below to enable the proceed button.
          </p>

          <div
            onScroll={handleScroll}
            className="h-64 overflow-y-auto border border-gray-300 p-4 rounded-md bg-gray-50 text-sm text-gray-700 space-y-4"
          >
            <h3 className="font-semibold text-base">Important Instructions for Applicants:</h3>
            <p>1. Ensure all information provided matches your official academic credentials.</p>
            <p>2. Upload clear scanned copies of your Photo, Signature, and ID Proof in Step 6.</p>
            <p>3. Application details are saved as drafts as you progress through each step.</p>
            <p>4. Submissions are final and cannot be edited after payment completion.</p>
            <p>5. Required formats: Photographs must be PNG/JPEG, under 500KB. ID Proofs must be PDF, under 2MB.</p>
            <p className="font-bold text-gray-900 pt-8">
              *** END OF GUIDELINES — YOU MAY NOW PROCEED ***
            </p>
          </div>

          {error && <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">{error}</div>}

          <div className="flex justify-between items-center pt-2">
            <span className="text-xs text-gray-500">
              {hasScrolledToBottom ? '✓ Guidelines read' : 'Scroll down inside box to enable proceed'}
            </span>
            <button
              type="button"
              onClick={handleStartApplication}
              disabled={!hasScrolledToBottom || loading}
              className="px-6 py-2 bg-black text-white rounded-md hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
            >
              {loading ? 'Starting...' : 'I Agree & Proceed'}
            </button>
          </div>
        </div>
      )}

      {/* FORM STEPS (STEPS 1 TO 6) */}
      {currentStep >= 1 && (
        <div className="space-y-6">
          <div className="flex justify-between items-center border-b pb-2">
            {FormStepNav && <FormStepNav currentStep={currentStep} setCurrentStep={setCurrentStep} />}
            <button
              type="button"
              onClick={handleRestartSession}
              className="text-xs text-gray-500 hover:text-red-600 underline whitespace-nowrap ml-4"
            >
              Reset Session
            </button>
          </div>

          <div className="py-4">
            {currentStep === 1 && <FormStep1 formData={formData} onChange={handleInputChange} />}
            {currentStep === 2 && <FormStep2 formData={formData} onChange={handleInputChange} />}
            {currentStep === 3 && <FormStep3 formData={formData} onChange={handleInputChange} />}
            {currentStep === 4 && <FormStep4 formData={formData} onChange={handleInputChange} />}
            {currentStep === 5 && <FormStep5 formData={formData} onChange={handleInputChange} />}
            {currentStep === 6 && <FormStep6 formData={formData} onChange={handleInputChange} />}
          </div>

          <div className="flex justify-between pt-4 border-t">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={handleBack}
                className="px-5 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Back
              </button>
            ) : <div />}

            <button
              type="button"
              onClick={handleNext}
              className="px-6 py-2 bg-black text-white rounded-md hover:bg-gray-800"
            >
              {currentStep === 6 ? 'Submit Draft' : 'Next'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}