import React, { useState, useEffect, useRef } from 'react';
import FormStep1 from '../components/FormStep1';
import FormStep2 from '../components/FormStep2';
import FormStep3 from '../components/FormStep3';
import FormStep4 from '../components/FormStep4';
import FormStep5 from '../components/FormStep5';
import FormStep6 from '../components/FormStep6';
import FormStep7 from '../components/FormStep7';
import FormStepNav from '../components/FormStepNav';
import { apiClient, applicationApi } from '../api/client';
import { useAutoSave } from '../hooks/useAutoSave';
import { useFormRehydrate } from '../hooks/useFormRehydrate';

// TODO: replace this placeholder with the exact guidelines text from the SRD.
const GUIDELINES = [
  'Please read these guidelines carefully before starting your application.',
  'All information you provide must be accurate and match your official documents.',
  'Your progress is saved automatically as you fill in each field.',
  'You will need a passport-size photograph (PNG), a signature (PNG) and an ID proof (PDF).',
  'Applications cannot be edited after payment is completed.',
  'Providing false information may lead to cancellation of your application.',
  'The application fee is non-refundable.',
  'Keep your registration details and receipts safe for future reference.',
  'By clicking "I Agree & Proceed" you confirm that you have read and accepted these guidelines.',
];

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && Object.getPrototypeOf(v) === Object.prototype;
}

function Guidelines({ onAgree, busy, error }) {
  const boxRef = useRef(null);
  const [atBottom, setAtBottom] = useState(false);

  const check = () => {
    const el = boxRef.current;
    if (!el) return;
    if (el.scrollHeight - el.scrollTop <= el.clientHeight + 1) setAtBottom(true);
  };

  useEffect(() => {
    check(); // short content that never needs scrolling
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-gray-800">Application Guidelines</h2>
      <div
        ref={boxRef}
        onScroll={check}
        className="h-24 overflow-y-auto border rounded-md p-4 bg-gray-50 space-y-3 text-sm text-gray-700"
      >
        {GUIDELINES.map((line, i) => (
          <p key={i}>{i + 1}. {line}</p>
        ))}
      </div>
      {!atBottom && (
        <p className="text-xs text-gray-500">Scroll to the bottom to enable the button.</p>
      )}
      {error && <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">{error}</div>}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onAgree}
          disabled={!atBottom || busy}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {busy ? 'Starting…' : 'I Agree & Proceed'}
        </button>
      </div>
    </div>
  );
}

export default function ApplicationForm() {
  const [phase, setPhase] = useState('loading'); // loading | guidelines | form | error
  const [loadError, setLoadError] = useState('');
  const [applicationId, setApplicationId] = useState(null);
  const [resumeId, setResumeId] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [draft, setDraft] = useState({});
  const [documents, setDocuments] = useState({});
  const [profile, setProfile] = useState(null);
  const [saveError, setSaveError] = useState('');
  const [agreeBusy, setAgreeBusy] = useState(false);
  const [agreeError, setAgreeError] = useState('');
  const busyRef = useRef(false);
  const resumedRef = useRef(false);

  const { status, triggerSave, saveNow } = useAutoSave({
    appId: applicationId,
    stepNum: currentStep >= 1 && currentStep <= 6 ? currentStep : null,
  });

  // 1. On load: find out whether the student already accepted the guidelines.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.get('/api/app/current');
        if (cancelled) return;
        const d = res.data?.data;
        if (d?.profile) setProfile(d.profile);
        if (!res.data?.success) {
          setLoadError('Could not load your application.');
          setPhase('error');
        } else if (d?.application_id && d.guidelines_accepted) {
          setApplicationId(d.application_id);
          setResumeId(d.application_id);
        } else {
          setPhase('guidelines');
        }
      } catch (err) {
        if (cancelled) return;
        setLoadError(
          err.response?.status === 401
            ? 'You are not logged in. Please log in and reload this page.'
            : 'Could not reach the server. Please try again.'
        );
        setPhase('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // 2. Load saved draft (resume path, and also right after the student agrees).
  const rehydrate = useFormRehydrate(resumeId);
  useEffect(() => {
    if (!resumeId || resumedRef.current) return;
    if (rehydrate.loaded) {
      resumedRef.current = true;
      setDraft(rehydrate.draft);
      setDocuments(rehydrate.documents);
      setCurrentStep(Math.min(6, Math.max(1, rehydrate.lastStep)));
      setPhase('form');
    } else if (rehydrate.error) {
      setLoadError(rehydrate.error);
      setPhase('error');
    }
  }, [resumeId, rehydrate]);

  // 3. "I Agree & Proceed": /app/start runs only here.
  const handleAgree = async () => {
    setAgreeBusy(true);
    setAgreeError('');
    try {
      const res = await applicationApi.start();
      const id = res.data?.data?.application_id;
      if (res.data?.success && id) {
        setApplicationId(id);
        setResumeId(id); // rehydrate effect moves us into the form
      } else {
        setAgreeError(res.data?.error || 'Could not start your application.');
        setAgreeBusy(false);
      }
    } catch (err) {
      setAgreeError(err.response?.data?.error || 'Could not start your application. Please try again.');
      setAgreeBusy(false);
    }
  };

  // Next: save the full step, advance ONLY if the save is confirmed (FR-6.2).
  const handleNext = async (stepData) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setSaveError('');
    try {
      if (!isPlainObject(stepData)) {
        setSaveError('Nothing to save for this step.');
        return;
      }
      const ok = await saveNow(stepData);
      if (!ok) {
        setSaveError('Could not save this step. Please check your connection and try again.');
        return;
      }
      setDraft((prev) => ({ ...prev, [String(currentStep)]: stepData }));
      setCurrentStep((s) => Math.min(s + 1, 7));
    } finally {
      busyRef.current = false;
    }
  };

  // Back: if the step passes its data, save it first; otherwise just go back.
  const handleBack = async (stepData) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setSaveError('');
    try {
      if (isPlainObject(stepData)) {
        const ok = await saveNow(stepData);
        if (!ok) {
          setSaveError('Could not save this step. Please check your connection and try again.');
          return;
        }
        setDraft((prev) => ({ ...prev, [String(currentStep)]: stepData }));
      }
      setCurrentStep((s) => Math.max(s - 1, 1));
    } finally {
      busyRef.current = false;
    }
  };

  // Clicking a completed step in the tracker.
  const goToStep = (n) => {
    if (busyRef.current) return;
    setSaveError('');
    setCurrentStep(n);
  };

  const handleDocumentUploaded = (docType, objectName) => {
    setDocuments((prev) => ({ ...prev, [`${docType}_url`]: objectName }));
  };

  if (phase === 'loading') {
    return <div className="max-w-4xl mx-auto p-6 my-8 text-gray-600">Loading your application…</div>;
  }

  if (phase === 'error') {
    return (
      <div className="max-w-4xl mx-auto p-6 my-8">
        <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">{loadError}</div>
      </div>
    );
  }

  if (phase === 'guidelines') {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md my-8">
        <Guidelines onAgree={handleAgree} busy={agreeBusy} error={agreeError} />
      </div>
    );
  }

  const stepData = draft[String(currentStep)] || {};
  const common = { applicationId, onAutoSave: triggerSave, profile };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md my-8">
      <FormStepNav currentStep={currentStep} setCurrentStep={goToStep} totalSteps={7} />

      {currentStep <= 6 && status !== 'idle' && (
        <div
          className={`text-sm font-medium mb-4 text-right ${
            status === 'failed' ? 'text-red-600' : status === 'saved' ? 'text-green-600' : 'text-blue-600'
          }`}
        >
          {status === 'saving' && 'Saving…'}
          {status === 'saved' && 'Saved ✓'}
          {status === 'failed' && 'Save failed'}
        </div>
      )}
      {saveError && (
        <div className="text-sm font-medium mb-4 p-3 bg-red-50 text-red-700 rounded border border-red-200">
          {saveError}
        </div>
      )}

      {currentStep === 1 && <FormStep1 {...common} initialData={stepData} onNext={handleNext} />}
      {currentStep === 2 && (
        <FormStep2 {...common} initialData={stepData} onNext={handleNext} onBack={handleBack} />
      )}
      {currentStep === 3 && (
        <FormStep3 {...common} initialData={stepData} onNext={handleNext} onBack={handleBack} />
      )}
      {currentStep === 4 && (
        <FormStep4 {...common} initialData={stepData} onNext={handleNext} onBack={handleBack} />
      )}
      {currentStep === 5 && (
        <FormStep5 {...common} initialData={stepData} onNext={handleNext} onBack={handleBack} />
      )}
      {currentStep === 6 && (
        <FormStep6
          {...common}
          initialData={{ ...stepData, ...documents }}
          onDocumentUploaded={handleDocumentUploaded}
          onNext={handleNext}
          onBack={handleBack}
        />
      )}
      {currentStep === 7 && <FormStep7 onBack={handleBack} />}
    </div>
  );
}
