'use client';

import { useId } from 'react';
import { useTranslations } from 'next-intl';
import { useIntakeStore } from '@/store/intakeStore';
import { Tooltip } from '@/components/ui/Tooltip';

const NITE_URL = 'https://www.nite.org.il';

interface Step2Errors {
  score?: string;
}

interface Step2Props {
  errors: Step2Errors;
}

export function Step2Psychometric({ errors }: Step2Props) {
  const t = useTranslations('intake');
  const headingId = useId();
  const inputId   = useId();
  const errId     = useId();
  const noteId    = useId();

  const {
    psychometricScore,
    haventTakenPsychometric,
    setPsychometricScore,
    setHaventTakenPsychometric,
  } = useIntakeStore();

  return (
    <section aria-labelledby={headingId} className="space-y-6">
      <div>
        <h2 id={headingId} className="text-xl font-bold text-gray-900">
          {t('step2.title')}
        </h2>
        <p className="mt-1 text-sm text-gray-500">{t('step2.description')}</p>
      </div>

      {/* Score input */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700"
          >
            {t('step2.scoreLabel')}
          </label>
          <Tooltip
            label={t('step2.tooltipButton')}
            content={
              <div className="space-y-2">
                <p>{t('step2.tooltipContent')}</p>
                <a
                  href={NITE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-primary-600 underline hover:text-primary-800"
                >
                  {t('step2.niteLink')} ↗
                </a>
              </div>
            }
          />
        </div>

        <input
          id={inputId}
          type="number"
          min={200}
          max={800}
          step={1}
          value={psychometricScore}
          placeholder={t('step2.scorePlaceholder')}
          disabled={haventTakenPsychometric}
          onChange={(e) => {
            const v = e.target.value === '' ? '' : Number(e.target.value);
            setPsychometricScore(v as number | '');
          }}
          aria-describedby={[
            errors.score ? errId : '',
            haventTakenPsychometric ? noteId : '',
          ]
            .filter(Boolean)
            .join(' ') || undefined}
          aria-invalid={!!errors.score}
          className={[
            'w-36 rounded-lg border px-3 py-2.5 text-sm transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-primary-500',
            haventTakenPsychometric
              ? 'cursor-not-allowed border-gray-200 bg-gray-100 text-gray-400'
              : errors.score
              ? 'border-red-400 bg-red-50 focus:ring-red-400'
              : 'border-gray-300 bg-white focus:border-primary-400',
          ].join(' ')}
        />

        {errors.score && (
          <p id={errId} role="alert" className="text-xs text-red-600">
            {errors.score}
          </p>
        )}
      </div>

      {/* "Haven't taken it yet" toggle */}
      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:bg-gray-50">
        <input
          type="checkbox"
          checked={haventTakenPsychometric}
          onChange={(e) => setHaventTakenPsychometric(e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        <div>
          <span className="block text-sm font-medium text-gray-800">
            {t('step2.haventTaken')}
          </span>
          {haventTakenPsychometric && (
            <span
              id={noteId}
              className="mt-0.5 block text-xs text-gray-500"
            >
              {t('step2.haventTakenNote')}
            </span>
          )}
        </div>
      </label>

      {/* NITE link (standalone, visible always) */}
      <a
        href={NITE_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-sm text-primary-600 underline hover:text-primary-800"
      >
        {t('step2.niteLink')}
        <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
          <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
        </svg>
      </a>
    </section>
  );
}
