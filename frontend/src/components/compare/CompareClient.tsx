'use client';

import React                from 'react';
import { useTranslations }  from 'next-intl';
import { useQueries }       from '@tanstack/react-query';
import { Link }             from '@/i18n/navigation';
import { useComparisonStore } from '@/store/comparisonStore';
import { useIntakeStore }     from '@/store/intakeStore';
import { fetchProgram }       from '@/lib/api';
import type { ProgramDetail, EligibilityResultItem } from '@/types';

// ── Demand badge ──────────────────────────────────────────────────────────────

const DEMAND_COLORS: Record<string, string> = {
  growing:   'bg-eligible-bg   text-eligible-text',
  stable:    'bg-primary-50    text-primary-800',
  declining: 'bg-borderline-bg text-borderline-text',
};

function DemandBadge({ trend }: { trend: string }) {
  const t = useTranslations('compare.demand');
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
        DEMAND_COLORS[trend] ?? 'bg-gray-100 text-gray-600'
      }`}
    >
      {t(trend as 'growing' | 'stable' | 'declining')}
    </span>
  );
}

// ── Eligibility badge ─────────────────────────────────────────────────────────

function EligibilityBadge({ result }: { result: EligibilityResultItem | undefined }) {
  const t = useTranslations('compare.eligibilityStatus');
  if (!result) return <span className="text-sm text-gray-400">{t('noData')}</span>;

  const { label, cls } = result.eligible
    ? { label: t('eligible'),   cls: 'bg-eligible-bg   text-eligible-text'   }
    : result.borderline
    ? { label: t('borderline'), cls: 'bg-borderline-bg text-borderline-text' }
    : { label: t('below'),      cls: 'bg-ineligible-bg text-ineligible-text' };

  return (
    <span className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${cls}`}>
      {label}
    </span>
  );
}

// ── Program column header ─────────────────────────────────────────────────────

function ProgramColumnHeader({
  program,
  onRemove,
}: {
  program:  ProgramDetail;
  onRemove: () => void;
}) {
  const t = useTranslations('compare');
  return (
    <div className="space-y-2 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="line-clamp-2 text-sm font-bold leading-tight text-gray-900">
            {program.name_he}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">{program.institution.name_he}</p>
        </div>
        <button
          type="button"
          aria-label={t('removeProgram')}
          onClick={onRemove}
          className="shrink-0 rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
        >
          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>
      <Link
        href={`/program/${program.id}`}
        className="inline-block rounded-lg border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
      >
        {t('viewProgram')} →
      </Link>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  const t = useTranslations('compare.empty');
  return (
    <div className="flex flex-col items-center gap-4 py-20 text-center">
      <svg
        className="h-16 w-16 text-gray-200"
        viewBox="0 0 64 64"
        fill="none"
        aria-hidden="true"
      >
        <rect x="4"  y="16" width="16" height="32" rx="3" stroke="currentColor" strokeWidth="2" />
        <rect x="24" y="16" width="16" height="32" rx="3" stroke="currentColor" strokeWidth="2" />
        <rect x="44" y="16" width="16" height="32" rx="3" stroke="currentColor" strokeWidth="2" />
      </svg>
      <div>
        <p className="text-base font-semibold text-gray-700">{t('title')}</p>
        <p className="mt-1 text-sm text-gray-500">{t('hint')}</p>
      </div>
      <Link
        href="/results"
        className="rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-700"
      >
        {t('cta')}
      </Link>
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 w-48 rounded-lg bg-gray-200" />
      <div className="grid grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="space-y-2 rounded-xl border border-gray-100 p-4">
            <div className="h-5 w-3/4 rounded bg-gray-200" />
            <div className="h-4 w-1/2 rounded bg-gray-200" />
          </div>
        ))}
      </div>
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="h-10 rounded-lg bg-gray-100" />
      ))}
    </div>
  );
}

// ── Row label + group header cell ─────────────────────────────────────────────

function LabelCell({
  rowLabel,
  groupLabel,
  isFirstInGroup,
  isLastRow,
}: {
  rowLabel:       string;
  groupLabel?:    string;
  isFirstInGroup: boolean;
  isLastRow:      boolean;
}) {
  return (
    <div
      className={[
        'flex flex-col justify-center bg-gray-50 px-4 py-3',
        isFirstInGroup ? 'border-t border-t-gray-200 pt-4' : '',
        isLastRow       ? '' : 'border-b border-gray-100',
      ].join(' ')}
    >
      {isFirstInGroup && groupLabel && (
        <span className="mb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400">
          {groupLabel}
        </span>
      )}
      <span className="text-sm text-gray-600">{rowLabel}</span>
    </div>
  );
}

// ── Value cell ────────────────────────────────────────────────────────────────

function ValueCell({
  children,
  isFirstInGroup,
  isLastRow,
}: {
  children:       React.ReactNode;
  isFirstInGroup: boolean;
  isLastRow:      boolean;
}) {
  return (
    <div
      className={[
        'flex items-center border-s border-gray-100 px-4 py-3',
        isFirstInGroup ? 'border-t border-t-gray-200 pt-4' : '',
        isLastRow       ? '' : 'border-b border-gray-100',
      ].join(' ')}
    >
      {children}
    </div>
  );
}

// ── Row groups and keys ───────────────────────────────────────────────────────

type RowKey =
  | 'eligibility' | 'yourSekem' | 'threshold' | 'margin'
  | 'field' | 'degree' | 'duration' | 'location' | 'tuition'
  | 'salary' | 'demand' | 'jobTitles'
  | 'pitch';

const ROW_GROUPS: Array<{ group: 'admission' | 'program' | 'career' | 'curriculum'; keys: RowKey[] }> = [
  { group: 'admission',  keys: ['eligibility', 'yourSekem', 'threshold', 'margin'] },
  { group: 'program',    keys: ['field', 'degree', 'duration', 'location', 'tuition'] },
  { group: 'career',     keys: ['salary', 'demand', 'jobTitles'] },
  { group: 'curriculum', keys: ['pitch'] },
];

// ── Main component ────────────────────────────────────────────────────────────

export function CompareClient() {
  const t       = useTranslations('compare');
  const tFields = useTranslations('intake.fields');

  const { selectedIds, removeProgram } = useComparisonStore();
  const eligibilityResults = useIntakeStore((s) => s.eligibilityResults);

  const queries = useQueries({
    queries: selectedIds.map((id) => ({
      queryKey:  ['program', id] as const,
      queryFn:   () => fetchProgram(id),
      staleTime: 1000 * 60 * 5,
    })),
  });

  const isLoading = queries.some((q) => q.isLoading);
  const programs  = queries
    .map((q) => q.data)
    .filter((p): p is ProgramDetail => p !== undefined);

  if (selectedIds.length === 0) return <EmptyState />;
  if (isLoading)                return <LoadingSkeleton />;
  if (programs.length === 0)    return <EmptyState />;

  const resultMap = new Map<string, EligibilityResultItem>(
    (eligibilityResults?.results ?? []).map((r) => [r.program.id, r])
  );

  // Build all flat rows with group metadata for rendering
  const allRows: Array<{
    key:            RowKey;
    group:          string;
    isFirstInGroup: boolean;
  }> = [];

  for (const { group, keys } of ROW_GROUPS) {
    keys.forEach((key, idx) => {
      allRows.push({ key, group, isFirstInGroup: idx === 0 });
    });
  }

  const colClass =
    programs.length === 1 ? 'grid-cols-[200px_1fr]'         :
    programs.length === 2 ? 'grid-cols-[200px_1fr_1fr]'     :
                            'grid-cols-[200px_1fr_1fr_1fr]';

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
        <Link
          href="/results"
          className="text-sm font-medium text-primary-600 hover:underline"
        >
          ← {t('backToResults')}
        </Link>
      </div>

      {/* Scrollable table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className={`grid min-w-[560px] ${colClass}`}>

          {/* ── Program header row ─────────────────────────────────────── */}
          <div className="border-b border-gray-200 bg-gray-50 p-3" />
          {programs.map((p) => (
            <div key={p.id} className="border-b border-s border-gray-200 bg-gray-50">
              <ProgramColumnHeader program={p} onRemove={() => removeProgram(p.id)} />
            </div>
          ))}

          {/* ── Data rows ─────────────────────────────────────────────── */}
          {allRows.map(({ key, group, isFirstInGroup }, rowIdx) => {
            const isLast = rowIdx === allRows.length - 1;
            const groupLabel = isFirstInGroup
              ? t(`groups.${group as 'admission' | 'program' | 'career' | 'curriculum'}`)
              : undefined;

            return (
              <React.Fragment key={key}>
                <LabelCell
                  rowLabel={t(`rows.${key}`)}
                  groupLabel={groupLabel}
                  isFirstInGroup={isFirstInGroup}
                  isLastRow={isLast}
                />
                {programs.map((p) => (
                  <ValueCell
                    key={`${p.id}-${key}`}
                    isFirstInGroup={isFirstInGroup}
                    isLastRow={isLast}
                  >
                    {renderValue(key, p, resultMap.get(p.id), t, tFields)}
                  </ValueCell>
                ))}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Value renderer (pure function, no hooks) ──────────────────────────────────

function renderValue(
  key:    RowKey,
  p:      ProgramDetail,
  result: EligibilityResultItem | undefined,
  t:      ReturnType<typeof useTranslations<'compare'>>,
  tFields: ReturnType<typeof useTranslations<'intake.fields'>>,
): React.ReactNode {
  switch (key) {
    case 'eligibility':
      return <EligibilityBadge result={result} />;

    case 'yourSekem':
      return result
        ? <span className="text-sm font-semibold text-gray-800">{result.sekem.toFixed(1)}</span>
        : <span className="text-sm text-gray-400">{t('values.noSekem')}</span>;

    case 'threshold':
      return p.latest_sekem_formula
        ? <span className="text-sm text-gray-700">{t('values.threshold', { value: p.latest_sekem_formula.threshold_sekem, year: p.latest_sekem_formula.year })}</span>
        : <span className="text-sm text-gray-400">{t('values.noSekem')}</span>;

    case 'margin': {
      if (!result) return <span className="text-sm text-gray-400">{t('values.noSekem')}</span>;
      const { margin } = result;
      const cls = margin >= 0 ? 'text-eligible-text' : 'text-ineligible-text';
      const txt = margin >= 0
        ? t('values.margin',    { margin })
        : t('values.marginNeg', { margin });
      return <span className={`text-sm font-semibold ${cls}`}>{txt}</span>;
    }

    case 'field':
      return (
        <span className="text-sm text-gray-700">
          {tFields(p.field as Parameters<typeof tFields>[0])}
        </span>
      );

    case 'degree':
      return <span className="text-sm text-gray-700">{p.degree_type}</span>;

    case 'duration':
      return <span className="text-sm text-gray-700">{t('values.duration', { years: p.duration_years })}</span>;

    case 'location':
      return <span className="text-sm text-gray-700">{p.location}</span>;

    case 'tuition':
      return p.tuition_annual_ils
        ? <span className="text-sm text-gray-700">{t('values.tuition', { amount: p.tuition_annual_ils.toLocaleString('he-IL') })}</span>
        : <span className="text-sm text-gray-400">{t('values.noTuition')}</span>;

    case 'salary': {
      const c = p.career_data;
      if (!c) return <span className="text-sm text-gray-400">{t('values.noSalary')}</span>;
      if (c.avg_salary_min_ils && c.avg_salary_max_ils) {
        return (
          <span className="text-sm text-gray-700">
            {t('values.salaryRange', {
              min: c.avg_salary_min_ils.toLocaleString('he-IL'),
              max: c.avg_salary_max_ils.toLocaleString('he-IL'),
            })}
          </span>
        );
      }
      if (c.avg_salary_min_ils) {
        return (
          <span className="text-sm text-gray-700">
            {t('values.salaryMinOnly', { min: c.avg_salary_min_ils.toLocaleString('he-IL') })}
          </span>
        );
      }
      return <span className="text-sm text-gray-400">{t('values.noSalary')}</span>;
    }

    case 'demand':
      return p.career_data
        ? <DemandBadge trend={p.career_data.demand_trend} />
        : <span className="text-sm text-gray-400">—</span>;

    case 'jobTitles': {
      const titles = p.career_data?.job_titles ?? [];
      if (titles.length === 0) return <span className="text-sm text-gray-400">{t('values.noJobTitles')}</span>;
      return (
        <div className="flex flex-wrap gap-1">
          {titles.slice(0, 3).map((j) => (
            <span key={j} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
              {j}
            </span>
          ))}
        </div>
      );
    }

    case 'pitch':
      return p.syllabus?.one_line_pitch_he
        ? <span className="text-sm text-gray-700">{p.syllabus.one_line_pitch_he}</span>
        : <span className="text-sm text-gray-400">{t('values.noPitch')}</span>;

    default:
      return null;
  }
}
