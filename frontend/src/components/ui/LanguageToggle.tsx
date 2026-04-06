'use client';

import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter } from 'next/navigation';
import { useTransition } from 'react';
import type { Locale } from '@/i18n/routing';

export function LanguageToggle() {
  const locale = useLocale() as Locale;
  const t = useTranslations('nav');
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const nextLocale: Locale = locale === 'he' ? 'en' : 'he';

  const switchLocale = () => {
    startTransition(() => {
      // Strip the current locale prefix (if any) and navigate to the same path
      const stripped = pathname.replace(/^\/(en|he)/, '') || '/';
      const target = nextLocale === 'he' ? stripped : `/${nextLocale}${stripped}`;
      router.push(target);
    });
  };

  return (
    <button
      type="button"
      onClick={switchLocale}
      disabled={isPending}
      aria-label={t('toggleLanguage')}
      className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500 disabled:opacity-50"
    >
      {t('toggleLanguage')}
    </button>
  );
}
