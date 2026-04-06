'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import type { EligibilityResultItem } from '@/types';
import { useComparisonStore, MAX_COMPARISON_PROGRAMS } from '@/store/comparisonStore';
import { FIELD_CODES, type FieldCode } from '@/types';

interface ProgramCardProps {
  item: EligibilityResultItem;
}

// ── Eligibility badge ─────────────────────────────────────────────────────────

function EligibilityBadge({
  eligible,
  borderline,
}: {
  eligible: boolean;
  borderline: boolean;
}) {
  const t = useTranslations('program.eligibility');

  if (eligible) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-green-500" />
        {t('eligible')}
      </span>
    );
  }
  if (borderline) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-semibold text-yellow-800">
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
        {t('borderline')}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800">
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-red-500" />
      {t('belowThreshold')}
    </span>
  );
}

// ── Field badge ───────────────────────────────────────────────────────────────

function FieldBadge({ field }: { field: string }) {
  const t = useTranslations('intake.fields');
  const isKnown = FIELD_CODES.includes(field as FieldCode);
  const label = isKnown ? t(field as FieldCode) : field;

  return (
    <span className="inline-block rounded-md bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700">
      {label}
    </span>
  );
}

// ── Sekem bar visualization ───────────────────────────────────────────────────

function SekemBar({
  sekem,
  threshold,
}: {
  sekem: number;
  threshold: number;
}) {
  // Show the user's sekem vs the threshold on a simple bar
  // Bar width represents sekem / 800 (max possible sekem score)
  const maxScore = 800;
  const userPct   = Math.min((sekem / maxScore) * 100, 100);
  const threshPct = Math.min((threshold / maxScore) * 100, 100);
  const eligible  = sekem >= threshold;

  return (
    <div className="space-y-1" aria-hidden="true">
      <div className="relative h-2 w-full rounded-full bg-gray-100">
        {/* Threshold marker */}
        <div
          className="absolute top-0 h-full w-0.5 -translate-x-1/2 rounded-full bg-gray-400"
          style={{ left: `${threshPct}%` }}
        />
        {/* User score fill */}
        <div
          className={[
            'h-full rounded-full transition-all',
            eligible ? 'bg-green-400' : sekem >= threshold - 30 ? 'bg-yellow-400' : 'bg-red-400',
          ].join(' ')}
          style={{ width: `${userPct}%` }}
        />
      </div>
    </div>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────

export function ProgramCard({ item }: ProgramCardProps) {
  const t = useTranslations('results.card');
  const { program, sekem, threshold, margin, eligible, borderline } = item;
  const { isSelected, toggleProgram, canAdd } = useComparisonStore();

  const selected    = isSelected(program.id);
  const disabled    = !selected && !canAdd();
  const roundedSekem = Math.round(sekem * 10) / 10;
  const roundedMargin = Math.round(Math.abs(margin) * 10) / 10;

  return (
    <article
      aria-label={program.name_he}
      className={[
        'group relative rounded-2xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md',
        selected ? 'border-primary-400 ring-2 ring-primary-300' : 'border-gray-200',
      ].join(' ')}
    >
      {/* ── Header row ─────────────────────────────────────────────────────── */}
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <Link
            href={`/program/${program.id}`}
            className="block text-base font-bold text-gray-900 hover:text-primary-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500"
          >
            {program.name_he}
          </Link>
          {program.name_en && (
            <p className="mt-0.5 text-xs text-gray-500">{program.name_en}</p>
          )}
          <p className="mt-1 text-sm text-gray-600">{program.institution.name_he}</p>
        </div>
        <EligibilityBadge eligible={eligible} borderline={borderline} />
      </div>

      {/* ── Badges row ─────────────────────────────────────────────────────── */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FieldBadge field={program.field} />
        <span className="text-xs text-gray-400">·</span>
        <span className="text-xs text-gray-500">
          {program.degree_type}
        </span>
        <span className="text-xs text-gray-400">·</span>
        <span className="text-xs text-gray-500">
          {t('duration', { years: program.duration_years })}
        </span>
        <span className="text-xs text-gray-400">·</span>
        <span className="text-xs text-gray-500">{program.location}</span>
      </div>

      {/* ── Sekem section ──────────────────────────────────────────────────── */}
      <div className="mb-3 space-y-2">
        <SekemBar sekem={sekem} threshold={threshold} />
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>
            {t('sekem')}: <strong className="text-gray-900">{roundedSekem}</strong>
          </span>
          <span>
            {t('threshold')}: <strong className="text-gray-900">{threshold}</strong>
          </span>
          <span
            className={
              margin >= 0 ? 'font-semibold text-green-700' : 'font-semibold text-red-600'
            }
          >
            {margin >= 0
              ? t('positiveMargin', { margin: roundedMargin })
              : t('negativeMargin', { margin: roundedMargin })}
          </span>
        </div>
      </div>

      {/* ── Footer: Compare + View ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-3">
        <button
          type="button"
          onClick={() => toggleProgram(program.id)}
          disabled={disabled}
          aria-pressed={selected}
          aria-label={selected ? t('compareAdded') : t('compare')}
          title={disabled ? t('compare') : undefined}
          className={[
            'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500',
            selected
              ? 'bg-primary-100 text-primary-800 hover:bg-primary-200'
              : disabled
              ? 'cursor-not-allowed text-gray-300'
              : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800',
          ].join(' ')}
        >
          {selected ? t('compareAdded') : t('compare')}
        </button>

        <Link
          href={`/program/${program.id}`}
          className="text-xs font-medium text-primary-600 hover:text-primary-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500"
          aria-label={`${t('viewDetails')}: ${program.name_he}`}
        >
          {t('viewDetails')} ←
        </Link>
      </div>
    </article>
  );
}
