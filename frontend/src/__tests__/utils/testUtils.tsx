import { ReactNode } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── next-intl mock ────────────────────────────────────────────────────────────
// Without params: returns the full dotted key so tests can assert on keys.
// With params: resolves the actual he.json value and substitutes params.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const _heMessages = require('../../../messages/he.json') as Record<string, unknown>;

function _resolveHeValue(fullKey: string): string | null {
  const parts = fullKey.split('.');
  let cur: unknown = _heMessages;
  for (const p of parts) {
    if (cur && typeof cur === 'object' && p in (cur as object)) {
      cur = (cur as Record<string, unknown>)[p];
    } else return null;
  }
  return typeof cur === 'string' ? cur : null;
}

jest.mock('next-intl', () => ({
  useTranslations: (ns?: string) => (key: string, params?: Record<string, unknown>) => {
    const full = ns ? `${ns}.${key}` : key;
    if (!params) return full;
    // With params: use actual translation template so interpolated values appear.
    const template = _resolveHeValue(full);
    const base = template ?? full;
    return Object.entries(params).reduce(
      (s, [k, v]) => s.replace(`{${k}}`, String(v)),
      base
    );
  },
  useLocale: () => 'he',
}));

jest.mock('next/navigation', () => ({
  useRouter:   () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/',
}));

jest.mock('@/i18n/navigation', () => ({
  useRouter:   () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/',
  Link:        ({ children, href }: { children: ReactNode; href: string }) =>
    <a href={href}>{children}</a>,
}));

// ── Zustand store reset ───────────────────────────────────────────────────────
// Call resetIntakeStore() in beforeEach to get a fresh store per test.
import { useIntakeStore } from '@/store/intakeStore';
export function resetIntakeStore() {
  useIntakeStore.getState().reset();
}

// ── Custom render with providers ──────────────────────────────────────────────
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function Wrapper({ children }: { children: ReactNode }) {
  const qc = makeQueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: Wrapper, ...options });
}

export * from '@testing-library/react';
export { renderWithProviders as render };
