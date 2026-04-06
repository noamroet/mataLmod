import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { IntakeWizard } from '@/components/intake/IntakeWizard';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('intake');
  return { title: t('title') };
}

export default function IntakePage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:py-12">
      <IntakeWizard />
    </main>
  );
}
