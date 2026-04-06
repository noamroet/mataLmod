'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { useComparisonStore } from '@/store/comparisonStore';
import type { EligibilityResultItem } from '@/types';

interface ComparisonBarProps {
  allItems: EligibilityResultItem[];
}

export function ComparisonBar({ allItems }: ComparisonBarProps) {
  const t = useTranslations('results.comparison');
  const { selectedIds, removeProgram, clearComparison } = useComparisonStore();

  if (selectedIds.length === 0) return null;

  // Resolve selected IDs → items
  const selectedItems = selectedIds
    .map((id) => allItems.find((item) => item.program.id === id))
    .filter((item): item is EligibilityResultItem => item !== undefined);

  return (
    <div
      role="region"
      aria-label={t('title')}
      className="fixed bottom-0 inset-x-0 z-30 animate-slide-up border-t border-gray-200 bg-white px-4 py-3 shadow-2xl sm:px-6"
    >
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
        {/* Selected chips */}
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          <span className="shrink-0 text-sm font-medium text-gray-700">
            {t('selected', { count: selectedIds.length })}:
          </span>
          {selectedItems.map((item) => (
            <span
              key={item.program.id}
              className="inline-flex max-w-[160px] items-center gap-1 rounded-full border border-primary-200 bg-primary-50 px-2 py-0.5 text-xs text-primary-800"
            >
              <span className="truncate">{item.program.name_he}</span>
              <button
                type="button"
                onClick={() => removeProgram(item.program.id)}
                aria-label={`${t('remove')} ${item.program.name_he}`}
                className="ml-0.5 shrink-0 rounded-full text-primary-500 hover:text-primary-800"
              >
                <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </span>
          ))}

          <button
            type="button"
            onClick={clearComparison}
            className="shrink-0 text-xs text-gray-400 underline hover:text-gray-700"
          >
            {t('clearAll')}
          </button>
        </div>

        {/* Compare CTA */}
        <Link
          href="/compare"
          className={[
            'shrink-0 rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors',
            selectedIds.length >= 2
              ? 'bg-primary-600 hover:bg-primary-700'
              : 'cursor-not-allowed bg-gray-300',
          ].join(' ')}
          aria-disabled={selectedIds.length < 2}
          tabIndex={selectedIds.length < 2 ? -1 : undefined}
        >
          {t('compareButton', { count: selectedIds.length })}
        </Link>
      </div>
    </div>
  );
}
