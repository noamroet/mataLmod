import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { fetchProgram } from '@/lib/api';
import { ProgramDetailClient } from '@/components/program/ProgramDetailClient';

// ── ISR: revalidate once a day ─────────────────────────────────────────────────

export const revalidate = 86400;

// ── Metadata ───────────────────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  try {
    const program = await fetchProgram(params.id);
    return {
      title: `${program.name_he} — ${program.institution.name_he}`,
      description: program.name_en ?? undefined,
    };
  } catch {
    return { title: 'תוכנית לימודים' };
  }
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default async function ProgramDetailPage({
  params,
}: {
  params: { id: string; locale: string };
}) {
  let program;
  try {
    program = await fetchProgram(params.id);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:py-10">
      <ProgramDetailClient program={program} />
    </main>
  );
}
