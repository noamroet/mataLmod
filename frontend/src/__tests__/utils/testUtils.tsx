import { ReactNode } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── next-intl mock ────────────────────────────────────────────────────────────
// Returns the translation key as the value for easy assertion.
jest.mock('next-intl', () => ({
  useTranslations: (ns?: string) => (key: string, params?: Record<string, unknown>) => {
    const full = ns ? `${ns}.${key}` : key;
    if (!params) return full;
    return Object.entries(params).reduce(
      (s, [k, v]) => s.replace(`{${k}}`, String(v)),
      full
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
