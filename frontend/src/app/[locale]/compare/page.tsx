import type { Metadata } from 'next';
import { CompareClient } from '@/components/compare/CompareClient';

export const metadata: Metadata = {
  title: 'השוואת תוכניות — מה תלמד?',
};

export default function ComparePage() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:py-10">
      <CompareClient />
    </main>
  );
}
