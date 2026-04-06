/**
 * Sentry browser-side initialisation.
 *
 * Loaded automatically by Next.js when @sentry/nextjs is installed.
 * Install: npm install @sentry/nextjs
 *
 * To enable: set NEXT_PUBLIC_SENTRY_DSN in your environment.
 * To disable: leave NEXT_PUBLIC_SENTRY_DSN unset or empty.
 */
import * as Sentry from '@sentry/nextjs';

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NODE_ENV,

    // Performance monitoring: capture 10% of transactions in production
    tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

    // Session replay: capture 10% of sessions, 100% of sessions with errors
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,

    // Don't send PII
    sendDefaultPii: false,

    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
  });
}
