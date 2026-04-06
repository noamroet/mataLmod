import { getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';

export default async function HomePage() {
  const t = await getTranslations('intake');

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-16 text-center">
      <h1 className="mb-4 text-4xl font-bold text-gray-900">{t('title')}</h1>
      <p className="mb-10 max-w-md text-lg text-gray-600">{t('subtitle')}</p>
      <Link
        href="/intake"
        className="rounded-xl bg-primary-600 px-8 py-4 text-lg font-semibold text-white shadow-md transition hover:bg-primary-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
      >
        {t('step1.title')}
      </Link>
    </main>
  );
}
