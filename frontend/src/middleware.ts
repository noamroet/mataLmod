import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['he', 'en'],
  defaultLocale: 'he',
  localePrefix: 'always',
  localeDetection: false, // always default to Hebrew, ignore Accept-Language header
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\..*).*)'],
};
