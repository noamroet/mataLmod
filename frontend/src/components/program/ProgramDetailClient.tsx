'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { EligibilitySection } from './EligibilitySection';
import { SyllabusSection }    from './SyllabusSection';
import { CareerSection }      from './CareerSection';
import { RoadmapSection }     from './RoadmapSection';
import { Breadcrumb }         from '@/components/ui/Breadcrumb';
import { AdvisorButton }      from '@/components/advisor/AdvisorButton';
import { WizardPanel }        from '@/components/advisor/WizardPanel';
import type { ProgramDetail } from '@/types';
import type { CtaSection }    from '@/lib/advisorFlows';

// ── Tab type ──────────────────────────────────────────────────────────────────

type ActiveTab = 'details' | 'roadmap';

// ── Header ─────────────────────────────────────────────────────────────────────

function ProgramHeader({ program }: { program: ProgramDetail }) {
  const t = useTranslations('programDetail.header');

  const isStale =
    program.data_freshness.last_scrape_success === null ||
    new Date().getTime() -
      new Date(program.data_freshness.last_scrape_success).getTime() >
      30 * 24 * 60 * 60 * 1000;

  return (
    <div className="space-y-3">
      {isStale && (
        <div
          role="alert"
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800"
        >
          {t('stalenessWarning')}
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">
            {program.name_he}
          </h1>
          {program.name_en && (
            <p className="text-sm text-gray-500">{program.name_en}</p>
          )}
          <p className="font-medium text-gray-700">{program.institution.name_he}</p>
        </div>

        <a
          href={program.official_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          {t('viewOfficial')}
          <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
            <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
          </svg>
        </a>
      </div>

      {/* Meta pills */}
      <div className="flex flex-wrap gap-3 text-sm text-gray-600">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1">
          <span className="font-medium">{t('degreeType')}:</span>
          {program.degree_type}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1">
          {t('duration', { years: program.duration_years })}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1">
          {t('location', { location: program.location })}
        </span>
        {program.tuition_annual_ils ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1">
            {t('tuition', { amount: program.tuition_annual_ils.toLocaleString('he-IL') })}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-gray-400">
            {t('noTuition')}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Institution section ───────────────────────────────────────────────────────

function InstitutionSection({ program }: { program: ProgramDetail }) {
  const t    = useTranslations('programDetail.institution');
  const inst = program.institution;

  return (
    <section aria-labelledby="institution-title" className="space-y-3">
      <h2 id="institution-title" className="text-lg font-bold text-gray-900">
        {t('title')}
      </h2>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
        <div>
          <p className="font-semibold text-gray-900">{inst.name_he}</p>
          <p className="text-sm text-gray-500">{inst.name_en}</p>
          <p className="text-sm text-gray-500">{inst.city_he}</p>
        </div>
        <a
          href={inst.website_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-primary-600 hover:underline"
        >
          {t('website')} →
        </a>
      </div>
    </section>
  );
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

function TabBar({
  active,
  onChange,
}: {
  active:   ActiveTab;
  onChange: (tab: ActiveTab) => void;
}) {
  const t = useTranslations('programDetail.tabs');

  const tabs: Array<{ id: ActiveTab; label: string }> = [
    { id: 'details', label: t('details') },
    { id: 'roadmap', label: t('roadmap') },
  ];

  return (
    <div role="tablist" aria-label="תפריט תוכן" className="flex gap-1 border-b border-gray-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          aria-controls={`tabpanel-${tab.id}`}
          id={`tab-${tab.id}`}
          type="button"
          onClick={() => onChange(tab.id)}
          className={[
            'px-4 py-2.5 text-sm font-medium transition-colors',
            active === tab.id
              ? 'border-b-2 border-primary-600 text-primary-700'
              : 'text-gray-500 hover:text-gray-700',
          ].join(' ')}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ── Main client component ─────────────────────────────────────────────────────

interface ProgramDetailClientProps {
  program: ProgramDetail;
}

export function ProgramDetailClient({ program }: ProgramDetailClientProps) {
  const tBreadcrumb = useTranslations('programDetail.breadcrumb');
  const tNav        = useTranslations('nav');

  const [activeTab,    setActiveTab]    = useState<ActiveTab>('details');

  // When the wizard CTA fires, switch to the right tab / scroll to section
  const handleWizardNavigate = (section: CtaSection) => {
    if (section === 'roadmap') {
      setActiveTab('roadmap');
      return;
    }
    setActiveTab('details');
    // Scroll to the relevant section after tab paint
    requestAnimationFrame(() => {
      const id =
        section === 'syllabus' ? 'syllabus-title'  :
        section === 'career'   ? 'career-title'    :
        null;
      if (id) document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    });
  };

  const breadcrumbItems = [
    { label: tNav('home'),            href: '/' },
    { label: tBreadcrumb('results'),  href: '/results' },
    { label: program.name_he },
  ];

  return (
    <>
      <Breadcrumb items={breadcrumbItems} />

      {/* Program header (always visible, above tabs) */}
      <ProgramHeader program={program} />

      <div className="mt-6">
        <TabBar active={activeTab} onChange={setActiveTab} />

        {/* ── פרטי התוכנית tab ─────────────────────────────────────────── */}
        <div
          id="tabpanel-details"
          role="tabpanel"
          aria-labelledby="tab-details"
          hidden={activeTab !== 'details'}
          className="mt-6"
        >
          <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
            {/* Main column */}
            <div className="space-y-8">
              <EligibilitySection program={program} />
              <hr className="border-gray-100" />
              <SyllabusSection syllabus={program.syllabus} />
              <hr className="border-gray-100" />
              <CareerSection career={program.career_data} />
              <hr className="border-gray-100" />
              <InstitutionSection program={program} />
            </div>

            {/* Sticky desktop sidebar */}
            <aside className="hidden lg:block">
              <div className="sticky top-6 space-y-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
                <EligibilitySection program={program} />
              </div>
            </aside>
          </div>
        </div>

        {/* ── מסלול קבלה tab ───────────────────────────────────────────── */}
        <div
          id="tabpanel-roadmap"
          role="tabpanel"
          aria-labelledby="tab-roadmap"
          hidden={activeTab !== 'roadmap'}
          className="mt-6"
        >
          <RoadmapSection program={program} />
        </div>
      </div>

      {/* Floating advisor button */}
      <AdvisorButton programId={program.id} />

      {/* Wizard advisor panel */}
      <WizardPanel onNavigate={handleWizardNavigate} />
    </>
  );
}
