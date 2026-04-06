import { useId } from 'react';
import { useTranslations } from 'next-intl';

export type SortOrder = 'margin' | 'alpha' | 'institution';

interface SortDropdownProps {
  value: SortOrder;
  onChange: (v: SortOrder) => void;
}

export function SortDropdown({ value, onChange }: SortDropdownProps) {
  const t = useTranslations('results.sort');
  const id = useId();

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="shrink-0 text-sm font-medium text-gray-700">
        {t('label')}:
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as SortOrder)}
        aria-label={t('ariaLabel')}
        className="rounded-lg border border-gray-300 bg-white py-1.5 ps-3 pe-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="margin">{t('margin')}</option>
        <option value="alpha">{t('alpha')}</option>
        <option value="institution">{t('institution')}</option>
      </select>
    </div>
  );
}
