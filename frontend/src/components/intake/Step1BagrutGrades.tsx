'use client';

import { useId } from 'react';
import { useTranslations } from 'next-intl';
import { useIntakeStore, weightedBagrutAverage } from '@/store/intakeStore';
import { SubjectCombobox } from './SubjectCombobox';
import { Button } from '@/components/ui/Button';
import { Tooltip } from '@/components/ui/Tooltip';
import type { SubjectCode } from '@/types';

interface Step1Errors {
  grades?: Record<string, { subject?: string; units?: string; grade?: string }>;
  estimatedAverage?: string;
  general?: string;
}

interface Step1Props {
  errors: Step1Errors;
}

export function Step1BagrutGrades({ errors }: Step1Props) {
  const t = useTranslations('intake');
  const headingId = useId();

  const {
    bagrutGrades,
    useEstimatedAverage,
    estimatedAverage,
    addGrade,
    updateGrade,
    removeGrade,
    setUseEstimatedAverage,
    setEstimatedAverage,
  } = useIntakeStore();

  const avg = weightedBagrutAverage(bagrutGrades);
  const usedSubjects = bagrutGrades.map((g) => g.subject).filter(Boolean);

  return (
    <section aria-labelledby={headingId} className="space-y-6">
      <div>
        <h2 id={headingId} className="text-xl font-bold text-gray-900">
          {t('step1.title')}
        </h2>
        <p className="mt-1 text-sm text-gray-500">{t('step1.description')}</p>
      </div>

      {/* "I don't remember" toggle */}
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={useEstimatedAverage}
          onChange={(e) => setUseEstimatedAverage(e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        <span className="text-sm text-gray-700">
          {t('step1.estimatedCheckbox')}
        </span>
      </label>

      {useEstimatedAverage ? (
        /* ── Estimated average input ─────────────────────────────────────── */
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            {t('step1.estimatedLabel')}
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={estimatedAverage}
            placeholder={t('step1.estimatedPlaceholder')}
            onChange={(e) => {
              const v = e.target.value === '' ? '' : Number(e.target.value);
              setEstimatedAverage(v as number | '');
            }}
            aria-describedby={errors.estimatedAverage ? 'estimated-error' : undefined}
            aria-invalid={!!errors.estimatedAverage}
            className={[
              'w-32 rounded-lg border px-3 py-2 text-sm',
              'focus:outline-none focus:ring-2 focus:ring-primary-500',
              errors.estimatedAverage
                ? 'border-red-400 bg-red-50'
                : 'border-gray-300',
            ].join(' ')}
          />
          {errors.estimatedAverage && (
            <p id="estimated-error" role="alert" className="text-xs text-red-600">
              {errors.estimatedAverage}
            </p>
          )}
        </div>
      ) : (
        <>
          {/* ── Subject rows ───────────────────────────────────────────────── */}
          {errors.general && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
              {errors.general}
            </p>
          )}

          <div className="space-y-3" role="list" aria-label="מקצועות בגרות">
            {bagrutGrades.map((row, idx) => {
              const rowErrors = errors.grades?.[row.id];
              const subjectId = `subject-${row.id}`;
              const unitsId   = `units-${row.id}`;
              const gradeId   = `grade-${row.id}`;
              const subjectLabelId = `${subjectId}-label`;
              const unitsErrId = `${unitsId}-err`;
              const gradeErrId = `${gradeId}-err`;
              const subjectErrId = `${subjectId}-err`;

              return (
                <div
                  key={row.id}
                  role="listitem"
                  aria-label={t('step1.rowCount', { n: idx + 1 })}
                  className="relative rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
                >
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto_auto_auto]">

                    {/* Subject combobox */}
                    <div className="space-y-1">
                      <label
                        id={subjectLabelId}
                        htmlFor={subjectId}
                        className="block text-xs font-medium text-gray-600"
                      >
                        {t('step1.subjectLabel')}
                      </label>
                      <SubjectCombobox
                        id={subjectId}
                        value={row.subject}
                        onChange={(code) => updateGrade(row.id, 'subject', code)}
                        usedSubjects={usedSubjects}
                        aria-labelledby={subjectLabelId}
                        aria-describedby={rowErrors?.subject ? subjectErrId : undefined}
                        hasError={!!rowErrors?.subject}
                      />
                      {rowErrors?.subject && (
                        <p id={subjectErrId} role="alert" className="text-xs text-red-600">
                          {rowErrors.subject}
                        </p>
                      )}
                    </div>

                    {/* Units selector */}
                    <div className="space-y-1">
                      <label
                        htmlFor={unitsId}
                        className="block text-xs font-medium text-gray-600"
                      >
                        {t('step1.unitsLabel')}
                      </label>
                      <select
                        id={unitsId}
                        value={row.units ?? ''}
                        onChange={(e) =>
                          updateGrade(
                            row.id,
                            'units',
                            e.target.value === '' ? null : (Number(e.target.value) as 3 | 4 | 5)
                          )
                        }
                        aria-describedby={rowErrors?.units ? unitsErrId : undefined}
                        aria-invalid={!!rowErrors?.units}
                        className={[
                          'rounded-lg border px-3 py-2 text-sm',
                          'focus:outline-none focus:ring-2 focus:ring-primary-500',
                          rowErrors?.units
                            ? 'border-red-400 bg-red-50'
                            : 'border-gray-300 bg-white',
                        ].join(' ')}
                      >
                        <option value="">{t('step1.selectUnits')}</option>
                        <option value="3">{t('step1.unitOption3')}</option>
                        <option value="4">{t('step1.unitOption4')}</option>
                        <option value="5">{t('step1.unitOption5')}</option>
                      </select>
                      {rowErrors?.units && (
                        <p id={unitsErrId} role="alert" className="text-xs text-red-600">
                          {rowErrors.units}
                        </p>
                      )}
                    </div>

                    {/* Grade input */}
                    <div className="space-y-1">
                      <label
                        htmlFor={gradeId}
                        className="block text-xs font-medium text-gray-600"
                      >
                        {t('step1.gradeLabel')}
                      </label>
                      <input
                        id={gradeId}
                        type="number"
                        min={0}
                        max={100}
                        value={row.grade}
                        placeholder={t('step1.gradePlaceholder')}
                        onChange={(e) =>
                          updateGrade(
                            row.id,
                            'grade',
                            e.target.value === '' ? '' : Number(e.target.value)
                          )
                        }
                        aria-describedby={rowErrors?.grade ? gradeErrId : undefined}
                        aria-invalid={!!rowErrors?.grade}
                        className={[
                          'w-20 rounded-lg border px-3 py-2 text-sm',
                          'focus:outline-none focus:ring-2 focus:ring-primary-500',
                          rowErrors?.grade
                            ? 'border-red-400 bg-red-50'
                            : 'border-gray-300 bg-white',
                        ].join(' ')}
                      />
                      {rowErrors?.grade && (
                        <p id={gradeErrId} role="alert" className="text-xs text-red-600">
                          {rowErrors.grade}
                        </p>
                      )}
                    </div>

                    {/* Remove button */}
                    {bagrutGrades.length > 1 && (
                      <div className="flex items-end pb-1">
                        <button
                          type="button"
                          onClick={() => removeGrade(row.id)}
                          aria-label={`${t('step1.removeSubject')} ${idx + 1}`}
                          className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-400"
                        >
                          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Add subject */}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={addGrade}
            className="gap-1"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            {t('step1.addSubject')}
          </Button>

          {/* Weighted average display */}
          {avg > 0 && (
            <div className="flex items-center gap-2 rounded-xl bg-primary-50 px-4 py-3">
              <span className="text-sm font-medium text-primary-800">
                {t('step1.weightedAverage')}:
              </span>
              <span
                className="text-xl font-bold text-primary-700"
                aria-live="polite"
                aria-atomic="true"
              >
                {avg.toFixed(1)}
              </span>
              <Tooltip
                label={t('step1.weightedAverageTooltip')}
                content={<p>{t('step1.weightedAverageTooltip')}</p>}
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}
