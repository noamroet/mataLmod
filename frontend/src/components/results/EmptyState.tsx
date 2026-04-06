import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';

interface EmptyStateProps {
  hasActiveFilters: boolean;
  onClearFilters: () => void;
}

export function EmptyState({ hasActiveFilters, onClearFilters }: EmptyStateProps) {
  const t = useTranslations('results');

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div
        aria-hidden="true"
        className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 text-3xl"
      >
        🔍
      </div>
      <h2 className="mb-2 text-lg font-semibold text-gray-800">{t('noResults')}</h2>
      <p className="mb-6 max-w-xs text-sm text-gray-500">{t('noResultsHint')}</p>
      {hasActiveFilters && (
        <Button variant="secondary" onClick={onClearFilters}>
          {t('noResultsClear')}
        </Button>
      )}
    </div>
  );
}
