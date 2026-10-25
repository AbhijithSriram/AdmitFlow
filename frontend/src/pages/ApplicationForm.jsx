import React, { useState, useEffect, useRef } from 'react';
import FormStep1 from '../components/FormStep1';
import FormStep2 from '../components/FormStep2';
import FormStep3 from '../components/FormStep3';
import FormStep4 from '../components/FormStep4';
import FormStep5 from '../components/FormStep5';
import FormStep6 from '../components/FormStep6';
import FormStep7 from '../components/FormStep7';
import FormStepNav from '../components/FormStepNav';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient, applicationApi } from '../api/client';
import AppHeader from '../components/AppHeader';
import { GUIDELINES, isUgProgramme } from '../content/institution';
import { useAutoSave } from '../hooks/useAutoSave';
import { useFormRehydrate } from '../hooks/useFormRehydrate';

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && Object.getPrototypeOf(v) === Object.prototype;
}

function Guidelines({ onAgree, busy, error }) {
  const [understood, setUnderstood] = useState(false);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-gray-800">Application Guidelines</h2>
      <ol className="border rounded-md p-4 bg-gray-50 space-y-3 text-sm text-gray-700 list-decimal list-inside">
        {GUIDELINES.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ol>
      <label className="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
        <input
          type="checkbox"
          checked={understood}
          onChange={(e) => setUnderstood(e.target.checked)}
          className="mt-0.5 h-4 w-4"
        />
        <span>I have read and understood the guidelines above.</span>
      </label>
      {error && <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm">{error}</div>}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onAgree}
          disabled={!understood || busy}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {busy ? 'Starting…' : 'I Agree & Proceed'}
        </button>
      </div>
    </div>
  );
}

function ApplicationFormBody() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState('loading'); // loading | guidelines | form | error
  const [loadError, setLoadError] = useState('');
  const [applicationId, setApplicationId] = useState(null);
  const [resumeId, setResumeId] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const askedStepRef = useRef(searchParams.get('step')); // the step in the URL when the page loaded
  const [resumeStep, setResumeStep] = useState(1); // where to land when the URL has no usable step
  const [furthest, setFurthest] = useState(1); // highest step the student may open
  const urlStep = Number.parseInt(searchParams.get('step') ?? '', 10);
  const currentStep =
    Number.isInteger(urlStep) && urlStep >= 1 && urlStep <= furthest ? urlStep : resumeStep;
  const goTo = (n) => setSearchParams({ step: String(n) });
  const [draft, setDraft] = useState({});
  const [documents, setDocuments] = useState({});
  const [profile, setProfile] = useState(null);
  const [saveError, setSaveError] = useState('');
  const [agreeBusy, setAgreeBusy] = useState(false);
  const [agreeError, setAgreeError] = useState('');
  const busyRef = useRef(false);
  const resumedRef = useRef(false);
  const draftRef = useRef({}); // always the latest draft, for callbacks that may hold an older closure
  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

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
        } else if (d?.status === 'PAID') {
          // Paid applications are final (the server refuses edits): nothing to fill in here.
          navigate('/dashboard', { replace: true });
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
      const resume = Math.min(6, Math.max(1, rehydrate.lastStep));
      const maxStep = Math.min(7, Math.max(1, rehydrate.lastStep + 1));
      const asked = Number.parseInt(askedStepRef.current ?? '', 10);
      const target = Number.isInteger(asked) && asked >= 1 && asked <= maxStep ? asked : resume;
      setResumeStep(resume);
      setFurthest(maxStep);
      setSearchParams({ step: String(target) }, { replace: true });
      setPhase('form');
    } else if (rehydrate.error) {
      setLoadError(rehydrate.error);
      setPhase('error');
    }
  }, [resumeId, rehydrate, setSearchParams]);

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

  // Step 4 asks different questions for undergraduate and postgraduate programmes. If the student
  // switches between the two, the answers saved for the other kind are cleared (and the step starts
  // blank) instead of lingering in the draft, the PDF and the admin's view.
  const resetAcademicIfLevelChanged = async (newProgramme) => {
    const current = draftRef.current;
    const academic = current['4'];
    const previous = current['3']?.programme;
    if (!academic || Object.keys(academic).length === 0 || !previous) return;
    if (isUgProgramme(previous) === isUgProgramme(newProgramme)) return;
    try {
      await applicationApi.saveDraftStep(applicationId, 4, {});
      draftRef.current = { ...draftRef.current, 4: {} };
      setDraft((prev) => ({ ...prev, 4: {} }));
    } catch {
      // Not fatal: Step 4 rebuilds its payload from the fields that apply when it is next saved.
    }
  };

  // Every auto-save also updates the local draft, so the browser Back/Forward buttons (which skip
  // Save & Next) never leave a step showing older answers. On Step 3 the undergraduate/postgraduate
  // check runs here too, so it applies however the student got to the step.
  const handleAutoSave = (data) => {
    triggerSave(data);
    if (!isPlainObject(data)) return;
    const step = currentStep;
    if (step === 3 && data.programme) resetAcademicIfLevelChanged(data.programme);
    draftRef.current = { ...draftRef.current, [String(step)]: data };
    setDraft((prev) => ({ ...prev, [String(step)]: data }));
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
      if (currentStep === 3) await resetAcademicIfLevelChanged(stepData.programme);
      const next = Math.min(currentStep + 1, 7);
      setFurthest((f) => Math.max(f, next));
      goTo(next);
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
      goTo(Math.max(currentStep - 1, 1));
    } finally {
      busyRef.current = false;
    }
  };

  // Clicking a completed step in the tracker.
  const goToStep = (n) => {
    if (busyRef.current) return;
    setSaveError('');
    goTo(n);
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
  const common = { applicationId, onAutoSave: handleAutoSave, profile };

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
        <FormStep4
          {...common}
          initialData={stepData}
          programme={draft['3']?.programme}
          onNext={handleNext}
          onBack={handleBack}
        />
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

export default function ApplicationForm() {
  return (
    <>
      <AppHeader />
      <ApplicationFormBody />
    </>
  );
}
