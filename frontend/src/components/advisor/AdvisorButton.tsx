'use client';

import { useTranslations } from 'next-intl';
import { useAdvisorStore } from '@/store/advisorStore';

interface AdvisorButtonProps {
  programId?: string | null;
}

export function AdvisorButton({ programId = null }: AdvisorButtonProps) {
  const t    = useTranslations('advisor');
  const open = useAdvisorStore((s) => s.open);

  return (
    <button
      type="button"
      onClick={() => open(programId)}
      className="fixed bottom-6 end-6 z-40 flex items-center gap-2 rounded-full bg-primary-600 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
      aria-label={t('buttonLabel')}
    >
      {/* Chat bubble icon */}
      <svg
        className="h-5 w-5 shrink-0"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2.024 21.5a.75.75 0 0 0 .976.976l4.332-1.414A9.953 9.953 0 0 0 12 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 1.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17z" />
      </svg>
      <span>{t('buttonLabel')}</span>
    </button>
  );
}
