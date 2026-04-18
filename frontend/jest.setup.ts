import '@testing-library/jest-dom';

// jsdom doesn't implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();

// jsdom doesn't implement crypto.randomUUID — polyfill with Node's implementation
Object.defineProperty(globalThis, 'crypto', {
  value: { randomUUID: () => require('node:crypto').randomUUID() },
});

// Mock next-intl so components render without a provider in unit tests.
// useTranslations returns a function that resolves message keys against the
// actual he.json messages file so tests can match real translated strings.
jest.mock('next-intl', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const he = require('./messages/he.json') as Record<string, unknown>;

  function resolve(obj: Record<string, unknown>, key: string): string {
    const parts = key.split('.');
    let cur: unknown = obj;
    for (const p of parts) {
      if (cur && typeof cur === 'object' && p in (cur as object)) {
        cur = (cur as Record<string, unknown>)[p];
      } else {
        return key;
      }
    }
    return typeof cur === 'string' ? cur : key;
  }

  function makeT(namespace: string) {
    return (key: string, params?: Record<string, unknown>): string => {
      const fullKey = namespace ? `${namespace}.${key}` : key;
      let str = resolve(he, fullKey);
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          str = str.replace(`{${k}}`, String(v));
        }
      }
      return str;
    };
  }

  return {
    useTranslations: (ns = '') => makeT(ns),
    useLocale: () => 'he',
    useFormatter: () => ({ number: (v: number) => String(v) }),
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
    getTranslations: async (ns = '') => makeT(typeof ns === 'string' ? ns : (ns as { namespace?: string }).namespace ?? ''),
  };
});
