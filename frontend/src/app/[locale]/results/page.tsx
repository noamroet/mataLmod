import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { ResultsClient } from '@/components/results/ResultsClient';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('results');
  return { title: t('title') };
}

export default function ResultsPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:py-10">
      <ResultsClient />
    </main>
  );
}
