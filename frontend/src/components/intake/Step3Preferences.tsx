'use client';

import { useId } from 'react';
import { useTranslations } from 'next-intl';
import { useIntakeStore } from '@/store/intakeStore';
import {
  FIELD_CODES,
  type FieldCode,
  type LocationFilter,
  type InstitutionTypeFilter,
  type StudyFormatFilter,
} from '@/types';

export function Step3Preferences() {
  const t       = useTranslations('intake');
  const tCommon = useTranslations('common');
  const headingId     = useId();
  const fieldGroupId  = useId();
  const locGroupId    = useId();
  const instGroupId   = useId();
  const fmtGroupId    = useId();

  const {
    fieldsOfInterest,
    location,
    institutionType,
    studyFormat,
    toggleField,
    setLocation,
    setInstitutionType,
    setStudyFormat,
  } = useIntakeStore();

  const locations: LocationFilter[] = ['all', 'north', 'center', 'south', 'jerusalem'];
  const institutionTypes: InstitutionTypeFilter[] = ['universities', 'all'];
  const studyFormats: StudyFormatFilter[] = ['full_time', 'part_time', 'any'];

  return (
    <section aria-labelledby={headingId} className="space-y-8">
      <div>
        <h2 id={headingId} className="text-xl font-bold text-gray-900">
          {t('step3.title')}
        </h2>
        <p className="mt-1 text-sm text-gray-500">{t('step3.description')}</p>
      </div>

      {/* ── Fields of interest ─────────────────────────────────────────────── */}
      <fieldset aria-labelledby={fieldGroupId}>
        <legend id={fieldGroupId} className="mb-3 text-sm font-semibold text-gray-800">
          {t('step3.fieldsTitle')}
          <span className="ms-2 text-xs font-normal text-gray-400">
            {tCommon('optional')}
          </span>
        </legend>
        <p className="mb-3 text-xs text-gray-500">{t('step3.fieldsDescription')}</p>
        <div className="flex flex-wrap gap-2" role="group">
          {FIELD_CODES.map((code) => {
            const selected = fieldsOfInterest.includes(code);
            return (
              <button
                key={code}
                type="button"
                role="checkbox"
                aria-checked={selected}
                onClick={() => toggleField(code)}
                className={[
                  'rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
                  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500',
                  selected
                    ? 'bg-primary-600 text-white hover:bg-primary-700'
                    : 'border border-gray-300 bg-white text-gray-700 hover:border-primary-400 hover:text-primary-700',
                ].join(' ')}
              >
                {t(`fields.${code}` as `fields.${FieldCode}`)}
              </button>
            );
          })}
        </div>
        {fieldsOfInterest.length > 0 && (
          <p
            className="mt-2 text-xs text-primary-600"
            aria-live="polite"
            aria-atomic="true"
          >
            {t('step3.selectedCount', { count: fieldsOfInterest.length })}
          </p>
        )}
      </fieldset>

      {/* ── Location ───────────────────────────────────────────────────────── */}
      <fieldset aria-labelledby={locGroupId}>
        <legend id={locGroupId} className="mb-3 text-sm font-semibold text-gray-800">
          {t('step3.locationTitle')}
        </legend>
        <div className="flex flex-wrap gap-2" role="group">
          {locations.map((loc) => {
            const selected = location === loc;
            return (
              <button
                key={loc}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setLocation(loc)}
                className={[
                  'rounded-full border px-3 py-1.5 text-sm font-medium transition-colors',
                  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500',
                  selected
                    ? 'border-primary-600 bg-primary-600 text-white'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-primary-400',
                ].join(' ')}
              >
                {t(`step3.locations.${loc}` as `step3.locations.${LocationFilter}`)}
              </button>
            );
          })}
        </div>
      </fieldset>

      {/* ── Institution type ───────────────────────────────────────────────── */}
      <fieldset aria-labelledby={instGroupId}>
        <legend id={instGroupId} className="mb-3 text-sm font-semibold text-gray-800">
          {t('step3.institutionTypeTitle')}
        </legend>
        <div className="flex gap-3">
          {institutionTypes.map((type) => {
            const selected = institutionType === type;
            return (
              <label
                key={type}
                className={[
                  'flex cursor-pointer items-center gap-2 rounded-lg border px-4 py-2.5 text-sm transition-colors',
                  selected
                    ? 'border-primary-500 bg-primary-50 text-primary-800 ring-1 ring-primary-400'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400',
                ].join(' ')}
              >
                <input
                  type="radio"
                  name="institutionType"
                  value={type}
                  checked={selected}
                  onChange={() => setInstitutionType(type)}
                  className="h-4 w-4 border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                {t(`step3.institutionTypes.${type}` as `step3.institutionTypes.${InstitutionTypeFilter}`)}
              </label>
            );
          })}
        </div>
      </fieldset>

      {/* ── Study format ───────────────────────────────────────────────────── */}
      <fieldset aria-labelledby={fmtGroupId}>
        <legend id={fmtGroupId} className="mb-3 text-sm font-semibold text-gray-800">
          {t('step3.studyFormatTitle')}
        </legend>
        <div className="flex gap-3 flex-wrap">
          {studyFormats.map((fmt) => {
            const selected = studyFormat === fmt;
            return (
              <label
                key={fmt}
                className={[
                  'flex cursor-pointer items-center gap-2 rounded-lg border px-4 py-2.5 text-sm transition-colors',
                  selected
                    ? 'border-primary-500 bg-primary-50 text-primary-800 ring-1 ring-primary-400'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400',
                ].join(' ')}
              >
                <input
                  type="radio"
                  name="studyFormat"
                  value={fmt}
                  checked={selected}
                  onChange={() => setStudyFormat(fmt)}
                  className="h-4 w-4 border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                {t(`step3.studyFormats.${fmt}` as `step3.studyFormats.${StudyFormatFilter}`)}
              </label>
            );
          })}
        </div>
      </fieldset>
    </section>
  );
}
