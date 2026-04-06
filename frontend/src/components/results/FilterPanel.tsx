'use client';

import {
  useRef,
  useEffect,
  useId,
  type ReactNode,
} from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import type { EligibilityResultItem } from '@/types';
import { FIELD_CODES, type FieldCode } from '@/types';

// ── Filter state type ─────────────────────────────────────────────────────────

export interface ResultFilters {
  institutions: string[];
  fields: string[];
  eligibilityStatus: Array<'eligible' | 'borderline' | 'below'>;
  locations: string[];
}

export const EMPTY_FILTERS: ResultFilters = {
  institutions:      [],
  fields:            [],
  eligibilityStatus: [],
  locations:         [],
};

export function countActiveFilters(f: ResultFilters): number {
  return (
    f.institutions.length +
    f.fields.length +
    f.eligibilityStatus.length +
    f.locations.length
  );
}

// ── Derived filter options from results ───────────────────────────────────────

export function deriveFilterOptions(items: EligibilityResultItem[]) {
  const institutionMap = new Map<string, string>();
  const fieldSet       = new Set<string>();
  const locationSet    = new Set<string>();

  for (const { program } of items) {
    institutionMap.set(program.institution_id, program.institution.name_he);
    fieldSet.add(program.field);
    locationSet.add(program.location);
  }

  return {
    institutions: Array.from(institutionMap.entries()).map(([id, name]) => ({ id, name })),
    fields:       Array.from(fieldSet),
    locations:    Array.from(locationSet),
  };
}

// ── Checkbox group helper ─────────────────────────────────────────────────────

function CheckboxGroup({
  legend,
  children,
}: {
  legend: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-xs font-semibold uppercase tracking-wide text-gray-500">
        {legend}
      </legend>
      {children}
    </fieldset>
  );
}

function CheckboxItem({
  id,
  checked,
  onChange,
  label,
  count,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  count?: number;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-2 rounded-lg p-1 hover:bg-gray-50">
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        <span className="text-sm text-gray-700">{label}</span>
      </div>
      {count !== undefined && (
        <span className="text-xs text-gray-400">{count}</span>
      )}
    </label>
  );
}

// ── FilterPanelContent ────────────────────────────────────────────────────────

function FilterPanelContent({
  filters,
  onChange,
  options,
  allItems,
}: {
  filters: ResultFilters;
  onChange: (f: ResultFilters) => void;
  options: ReturnType<typeof deriveFilterOptions>;
  allItems: EligibilityResultItem[];
}) {
  const t        = useTranslations('results.filters');
  const tFields  = useTranslations('intake.fields');
  const activeN  = countActiveFilters(filters);

  const toggle = <K extends keyof ResultFilters>(
    key: K,
    value: ResultFilters[K][number]
  ) => {
    const current = filters[key] as string[];
    const next = current.includes(value as string)
      ? current.filter((v) => v !== value)
      : [...current, value as string];
    onChange({ ...filters, [key]: next } as ResultFilters);
  };

  // Count how many items match each filter option (across all items, not filtered)
  const countForField = (field: string) =>
    allItems.filter((i) => i.program.field === field).length;
  const countForInst = (instId: string) =>
    allItems.filter((i) => i.program.institution_id === instId).length;
  const countForLoc = (loc: string) =>
    allItems.filter((i) => i.program.location === loc).length;
  const countEligible    = allItems.filter((i) => i.eligible).length;
  const countBorderline  = allItems.filter((i) => i.borderline).length;
  const countBelow       = allItems.filter((i) => !i.eligible && !i.borderline).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-gray-900">{t('title')}</h2>
        {activeN > 0 && (
          <button
            type="button"
            onClick={() => onChange(EMPTY_FILTERS)}
            className="text-xs text-primary-600 underline hover:text-primary-800"
          >
            {t('clearAll')}
          </button>
        )}
      </div>
      {activeN > 0 && (
        <p aria-live="polite" className="text-xs text-primary-600">
          {t('activeCount', { count: activeN })}
        </p>
      )}

      {/* Eligibility */}
      <CheckboxGroup legend={t('eligibility')}>
        <CheckboxItem
          id="filter-eligible"
          checked={filters.eligibilityStatus.includes('eligible')}
          onChange={() => toggle('eligibilityStatus', 'eligible')}
          label={t('eligible')}
          count={countEligible}
        />
        <CheckboxItem
          id="filter-borderline"
          checked={filters.eligibilityStatus.includes('borderline')}
          onChange={() => toggle('eligibilityStatus', 'borderline')}
          label={t('borderline')}
          count={countBorderline}
        />
        <CheckboxItem
          id="filter-below"
          checked={filters.eligibilityStatus.includes('below')}
          onChange={() => toggle('eligibilityStatus', 'below')}
          label={t('below')}
          count={countBelow}
        />
      </CheckboxGroup>

      {/* Institution */}
      {options.institutions.length > 1 && (
        <CheckboxGroup legend={t('institution')}>
          {options.institutions.map(({ id, name }) => (
            <CheckboxItem
              key={id}
              id={`filter-inst-${id}`}
              checked={filters.institutions.includes(id)}
              onChange={() => toggle('institutions', id)}
              label={name}
              count={countForInst(id)}
            />
          ))}
        </CheckboxGroup>
      )}

      {/* Field */}
      {options.fields.length > 1 && (
        <CheckboxGroup legend={t('field')}>
          {options.fields.map((field) => (
            <CheckboxItem
              key={field}
              id={`filter-field-${field}`}
              checked={filters.fields.includes(field)}
              onChange={() => toggle('fields', field)}
              label={
                FIELD_CODES.includes(field as FieldCode)
                  ? tFields(field as FieldCode)
                  : field
              }
              count={countForField(field)}
            />
          ))}
        </CheckboxGroup>
      )}

      {/* Location */}
      {options.locations.length > 1 && (
        <CheckboxGroup legend={t('location')}>
          {options.locations.map((loc) => (
            <CheckboxItem
              key={loc}
              id={`filter-loc-${loc}`}
              checked={filters.locations.includes(loc)}
              onChange={() => toggle('locations', loc)}
              label={loc}
              count={countForLoc(loc)}
            />
          ))}
        </CheckboxGroup>
      )}
    </div>
  );
}

// ── Mobile drawer ─────────────────────────────────────────────────────────────

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

function MobileDrawer({ open, onClose, children }: MobileDrawerProps) {
  const firstFocusRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      firstFocusRef.current?.focus();
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  const t = useTranslations('results.filters');

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('title')}
      className="fixed inset-0 z-40 flex flex-col justify-end"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet */}
      <div className="relative z-50 max-h-[85vh] overflow-y-auto rounded-t-2xl bg-white p-5 shadow-2xl animate-slide-up">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-base font-bold text-gray-900">{t('title')}</span>
          <button
            ref={firstFocusRef}
            type="button"
            onClick={onClose}
            aria-label={t('close')}
            className="rounded-full p-1 text-gray-500 hover:bg-gray-100"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        {children}
        <div className="sticky bottom-0 bg-white pt-4">
          <Button className="w-full" onClick={onClose}>
            {t('close')}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Public FilterPanel ─────────────────────────────────────────────────────────

interface FilterPanelProps {
  filters: ResultFilters;
  onChange: (f: ResultFilters) => void;
  allItems: EligibilityResultItem[];
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function FilterPanel({
  filters,
  onChange,
  allItems,
  mobileOpen,
  onMobileClose,
}: FilterPanelProps) {
  const options = deriveFilterOptions(allItems);
  const content = (
    <FilterPanelContent
      filters={filters}
      onChange={onChange}
      options={options}
      allItems={allItems}
    />
  );

  return (
    <>
      {/* Desktop sidebar — hidden on mobile */}
      <aside className="hidden w-60 shrink-0 lg:block">
        <div className="sticky top-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          {content}
        </div>
      </aside>

      {/* Mobile drawer */}
      <MobileDrawer open={mobileOpen} onClose={onMobileClose}>
        {content}
      </MobileDrawer>
    </>
  );
}
