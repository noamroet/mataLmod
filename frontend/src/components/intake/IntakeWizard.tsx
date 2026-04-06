'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useIntakeStore } from '@/store/intakeStore';
import { calculateEligibility, ApiError } from '@/lib/api';
import { buildEligibilityRequest } from '@/lib/utils';
import { ProgressBar } from './ProgressBar';
import { Step1BagrutGrades } from './Step1BagrutGrades';
import { Step2Psychometric } from './Step2Psychometric';
import { Step3Preferences } from './Step3Preferences';
import { Button } from '@/components/ui/Button';
import { LanguageToggle } from '@/components/ui/LanguageToggle';

// ── Validation ────────────────────────────────────────────────────────────────

type Step1Errors = {
  grades?: Record<string, { subject?: string; units?: string; grade?: string }>;
  estimatedAverage?: string;
  general?: string;
};

type Step2Errors = { score?: string };

function validateStep1(
  bagrutGrades: ReturnType<typeof useIntakeStore.getState>['bagrutGrades'],
  useEstimated: boolean,
  estimatedAverage: number | '',
  t: (key: string) => string
): Step1Errors {
  if (useEstimated) {
    if (estimatedAverage === '' || estimatedAverage < 0 || estimatedAverage > 100) {
      return { estimatedAverage: t('step1.validation.estimatedRange') };
    }
    return {};
  }

  if (bagrutGrades.length === 0) {
    return { general: t('step1.validation.atLeastOne') };
  }

  const gradeErrors: Step1Errors['grades'] = {};
  let hasAny = false;

  for (const row of bagrutGrades) {
    const rowErr: { subject?: string; units?: string; grade?: string } = {};
    if (!row.subject) rowErr.subject = t('step1.validation.subjectRequired');
    if (!row.units)   rowErr.units   = t('step1.validation.unitsRequired');
    if (row.grade === '') {
      rowErr.grade = t('step1.validation.gradeRequired');
    } else if ((row.grade as number) < 0 || (row.grade as number) > 100) {
      rowErr.grade = t('step1.validation.gradeRange');
    } else {
      hasAny = true;
    }
    if (Object.keys(rowErr).length > 0) gradeErrors[row.id] = rowErr;
  }

  if (!hasAny && bagrutGrades.every((g) => g.grade === '')) {
    return { general: t('step1.validation.atLeastOne') };
  }

  return Object.keys(gradeErrors).length > 0 ? { grades: gradeErrors } : {};
}

function validateStep2(
  score: number | '',
  haventTaken: boolean,
  t: (key: string) => string
): Step2Errors {
  if (haventTaken) return {};
  if (score === '') return { score: t('step2.validation.required') };
  if ((score as number) < 200 || (score as number) > 800) {
    return { score: t('step2.validation.range') };
  }
  return {};
}

// ── Component ─────────────────────────────────────────────────────────────────

export function IntakeWizard() {
  const t      = useTranslations('intake');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const store = useIntakeStore();
  const { currentStep, setStep } = store;

  const [step1Errors, setStep1Errors] = useState<Step1Errors>({});
  const [step2Errors, setStep2Errors] = useState<Step2Errors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Move focus to the top of the form on step change
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    headingRef.current?.focus();
  }, [currentStep]);

  const goBack = () => {
    setStep((currentStep - 1) as 1 | 2 | 3);
    setStep1Errors({});
    setStep2Errors({});
    setSubmitError(null);
  };

  const goNext = () => {
    if (currentStep === 1) {
      const errs = validateStep1(
        store.bagrutGrades,
        store.useEstimatedAverage,
        store.estimatedAverage,
        (k) => t(k as Parameters<typeof t>[0])
      );
      setStep1Errors(errs);
      if (Object.keys(errs).length === 0) setStep(2);
    } else if (currentStep === 2) {
      const errs = validateStep2(
        store.psychometricScore,
        store.haventTakenPsychometric,
        (k) => t(k as Parameters<typeof t>[0])
      );
      setStep2Errors(errs);
      if (Object.keys(errs).length === 0) setStep(3);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const request = buildEligibilityRequest({
        bagrutGrades:            store.bagrutGrades,
        useEstimatedAverage:     store.useEstimatedAverage,
        estimatedAverage:        store.estimatedAverage,
        psychometricScore:       store.psychometricScore,
        haventTakenPsychometric: store.haventTakenPsychometric,
        fieldsOfInterest:        store.fieldsOfInterest,
        location:                store.location,
        institutionType:         store.institutionType,
      });

      const results = await calculateEligibility(request);
      console.log('[IntakeWizard] API returned results:', results?.results?.length, 'items');
      store.setEligibilityResults(results);
      // Belt-and-suspenders: also save to sessionStorage so results page
      // can recover them even if Zustand hydration races.
      sessionStorage.setItem('mataLmod-results', JSON.stringify(results));
      console.log('[IntakeWizard] store set, navigating to results');

      router.push('/he/results');
    } catch (err) {
      if (err instanceof ApiError && err.status >= 500) {
        setSubmitError(t('submit.networkError'));
      } else {
        setSubmitError(t('submit.error'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top bar: title + language toggle */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1
            ref={headingRef}
            tabIndex={-1}
            className="text-2xl font-bold text-gray-900 focus:outline-none sm:text-3xl"
          >
            {t('title')}
          </h1>
          <p className="mt-1 text-sm text-gray-500">{t('subtitle')}</p>
        </div>
        <LanguageToggle />
      </div>

      {/* Progress */}
      <ProgressBar currentStep={currentStep} />

      {/* Step content */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        {currentStep === 1 && <Step1BagrutGrades errors={step1Errors} />}
        {currentStep === 2 && <Step2Psychometric errors={step2Errors} />}
        {currentStep === 3 && <Step3Preferences />}

        {/* Submit error */}
        {submitError && (
          <div
            role="alert"
            className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {submitError}
          </div>
        )}
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between gap-4">
        {currentStep > 1 ? (
          <Button
            type="button"
            variant="secondary"
            onClick={goBack}
            disabled={isSubmitting}
          >
            {tCommon('back')}
          </Button>
        ) : (
          <span aria-hidden="true" />
        )}

        {currentStep < 3 ? (
          <Button type="button" onClick={goNext}>
            {tCommon('next')}
          </Button>
        ) : (
          <Button
            type="button"
            onClick={handleSubmit}
            loading={isSubmitting}
            size="lg"
          >
            {isSubmitting ? t('submit.calculating') : tCommon('submit')}
          </Button>
        )}
      </div>
    </div>
  );
}
