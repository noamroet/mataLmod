'use client';

import { useState, useMemo, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { useIntakeStore } from '@/store/intakeStore';
import { useComparisonStore } from '@/store/comparisonStore';
import { ProgramCard } from './ProgramCard';
import { FilterPanel, EMPTY_FILTERS, countActiveFilters, type ResultFilters } from './FilterPanel';
import { SortDropdown, type SortOrder } from './SortDropdown';
import { ComparisonBar } from './ComparisonBar';
import { EmptyState } from './EmptyState';
import type { EligibilityResultItem } from '@/types';

// ── Sorting ───────────────────────────────────────────────────────────────────

function sortItems(items: EligibilityResultItem[], order: SortOrder): EligibilityResultItem[] {
  return [...items].sort((a, b) => {
    switch (order) {
      case 'margin': {
        const ga = a.eligible ? 0 : a.borderline ? 1 : 2;
        const gb = b.eligible ? 0 : b.borderline ? 1 : 2;
        if (ga !== gb) return ga - gb;
        return b.margin - a.margin;
      }
      case 'alpha':
        return a.program.name_he.localeCompare(b.program.name_he, 'he');
      case 'institution':
        return a.program.institution.name_he.localeCompare(
          b.program.institution.name_he,
          'he'
        );
    }
  });
}

// ── Filtering ─────────────────────────────────────────────────────────────────

function filterItems(
  items: EligibilityResultItem[],
  filters: ResultFilters
): EligibilityResultItem[] {
  return items.filter((item) => {
    if (
      filters.institutions.length > 0 &&
      !filters.institutions.includes(item.program.institution_id)
    )
      return false;

    if (filters.fields.length > 0 && !filters.fields.includes(item.program.field))
      return false;

    if (filters.locations.length > 0 && !filters.locations.includes(item.program.location))
      return false;

    if (filters.eligibilityStatus.length > 0) {
      const matchEligible    = filters.eligibilityStatus.includes('eligible') && item.eligible;
      const matchBorderline  = filters.eligibilityStatus.includes('borderline') && item.borderline;
      const matchBelow       = filters.eligibilityStatus.includes('below') && !item.eligible && !item.borderline;
      if (!matchEligible && !matchBorderline && !matchBelow) return false;
    }

    return true;
  });
}

// ── Institution group header (used when sorting by institution) ───────────────

function InstitutionGroupHeader({
  name,
  updatedAt,
}: {
  name: string;
  updatedAt: string | null;
}) {
  const t = useTranslations('results.institutionGroup');
  const date = updatedAt
    ? new Intl.DateTimeFormat('he-IL', { dateStyle: 'medium' }).format(
        new Date(updatedAt)
      )
    : null;

  return (
    <div className="flex items-baseline justify-between border-b border-gray-200 pb-2">
      <h2 className="text-base font-bold text-gray-800">{name}</h2>
      {date && (
        <span className="text-xs text-gray-400">{t('dataAsOf', { date })}</span>
      )}
    </div>
  );
}

// ── Profile summary pill ──────────────────────────────────────────────────────

function ProfileSummaryBar() {
  const t       = useTranslations('results.profileSummary');
  const summary = useIntakeStore((s) => s.eligibilityResults?.profile_summary);

  if (!summary) return null;

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-xl bg-primary-50 px-4 py-3 text-sm">
      <span className="font-semibold text-primary-900">{t('title')}:</span>
      <span className="text-primary-800">
        {t('average')}:{' '}
        <strong>{summary.bagrut_average.toFixed(1)}</strong>
      </span>
      <span className="text-primary-800">
        {t('psychometric')}:{' '}
        <strong>
          {summary.psychometric ?? t('notTaken')}
        </strong>
      </span>
      <span className="text-primary-800">
        {summary.subject_count} {t('subjects')}
      </span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function ResultsClient() {
  const t      = useTranslations('results');
  const router = useRouter();

  const storeResults = useIntakeStore((s) => s.eligibilityResults);
  const { selectedIds } = useComparisonStore();

  const [filters, setFilters]           = useState<ResultFilters>(EMPTY_FILTERS);
  const [sortOrder, setSortOrder]       = useState<SortOrder>('margin');
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  // Recover results from sessionStorage if the Zustand store is empty
  // (e.g. if Zustand hydration raced and overwrote the in-memory value).
  const [results, setResults] = useState(storeResults);
  const setEligibilityResults = useIntakeStore((s) => s.setEligibilityResults);

  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const raw = typeof window !== 'undefined'
      ? sessionStorage.getItem('mataLmod-results')
      : null;
    const sessionResults = raw ? JSON.parse(raw) : null;

    const effective = storeResults ?? sessionResults;
    if (effective && !storeResults) {
      setEligibilityResults(effective);
    }
    setResults(effective);
    setMounted(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mounted) return;
    if (!results) router.replace('/he/intake');
  }, [mounted, results, router]);

  const allItems = results?.results ?? [];

  const filtered = useMemo(() => filterItems(allItems, filters), [allItems, filters]);
  const sorted   = useMemo(() => sortItems(filtered, sortOrder), [filtered, sortOrder]);

  // For "sort by institution" — group results
  const groupedByInstitution = useMemo(() => {
    if (sortOrder !== 'institution') return null;
    const groups = new Map<string, { name: string; updatedAt: string | null; items: EligibilityResultItem[] }>();
    for (const item of sorted) {
      const id = item.program.institution_id;
      if (!groups.has(id)) {
        // Latest updated_at for this institution across all items (not just visible)
        const instItems = allItems.filter((i) => i.program.institution_id === id);
        const latestAt = instItems.reduce<string | null>((max, i) => {
          if (!max || i.program.updated_at > max) return i.program.updated_at;
          return max;
        }, null);
        groups.set(id, { name: item.program.institution.name_he, updatedAt: latestAt, items: [] });
      }
      groups.get(id)!.items.push(item);
    }
    return groups;
  }, [sorted, sortOrder, allItems]);

  const activeFilterCount = countActiveFilters(filters);

  if (!results) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">{t('redirecting')}</p>
      </div>
    );
  }

  return (
    /* Padding at bottom so comparison bar doesn't overlap last card */
    <div className={selectedIds.length > 0 ? 'pb-20' : ''}>
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="mb-6 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">
              {t('title')}
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              {activeFilterCount > 0
                ? t('subtitleFiltered', { shown: sorted.length, total: allItems.length })
                : t('subtitle', { total: allItems.length })}
            </p>
          </div>
          <Link
            href="/intake"
            className="shrink-0 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
          >
            {t('recalculate')}
          </Link>
        </div>

        <ProfileSummaryBar />
      </div>

      {/* ── Layout: sidebar + content ─────────────────────────────────────── */}
      <div className="flex gap-6">
        {/* Sidebar (desktop) + mobile sheet */}
        <FilterPanel
          filters={filters}
          onChange={setFilters}
          allItems={allItems}
          mobileOpen={mobileFilterOpen}
          onMobileClose={() => setMobileFilterOpen(false)}
        />

        {/* Main content */}
        <div className="min-w-0 flex-1 space-y-4">
          {/* Toolbar: mobile filter button + sort */}
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setMobileFilterOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 lg:hidden"
              aria-expanded={mobileFilterOpen}
            >
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3 5a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm2 5a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
              </svg>
              {t('filters.openButton')}
              {activeFilterCount > 0 && (
                <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-primary-600 text-[10px] text-white">
                  {activeFilterCount}
                </span>
              )}
            </button>

            <div className="ms-auto">
              <SortDropdown value={sortOrder} onChange={setSortOrder} />
            </div>
          </div>

          {/* Results list */}
          {sorted.length === 0 ? (
            <EmptyState
              hasActiveFilters={activeFilterCount > 0}
              onClearFilters={() => setFilters(EMPTY_FILTERS)}
            />
          ) : groupedByInstitution ? (
            /* Grouped view (sort by institution) */
            <div className="space-y-8">
              {Array.from(groupedByInstitution.values()).map((group) => (
                <section key={group.name}>
                  <InstitutionGroupHeader
                    name={group.name}
                    updatedAt={group.updatedAt}
                  />
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    {group.items.map((item) => (
                      <ProgramCard key={item.program.id} item={item} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            /* Flat list view (sort by margin or alpha) */
            <div
              aria-label={`${sorted.length} תוצאות`}
              className="grid gap-4 sm:grid-cols-2"
            >
              {sorted.map((item) => (
                <ProgramCard key={item.program.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Floating comparison bar */}
      <ComparisonBar allItems={allItems} />
    </div>
  );
}
