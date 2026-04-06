import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['he', 'en'],
  defaultLocale: 'he',
  localePrefix: 'always', // /he/... for Hebrew, /en/... for English
});

export type Locale = (typeof routing.locales)[number];
