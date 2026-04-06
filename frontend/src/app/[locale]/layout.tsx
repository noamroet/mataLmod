import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { QueryProvider } from '@/components/providers/QueryProvider';
import '../globals.css';

export const metadata: Metadata = {
  title: {
    default: 'MaTaLmod — מה תלמד?',
    template: '%s | MaTaLmod',
  },
  description: 'גלה אילו תארים מחכים לך — גישה חכמה לבחירת לימודים אקדמיים בישראל',
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: { locale: string };
}) {
  const { locale } = params;
  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <QueryProvider>
        {children}
      </QueryProvider>
    </NextIntlClientProvider>
  );
}
