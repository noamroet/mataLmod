'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { useIntakeStore } from '@/store/intakeStore';
import type {
  BagrutGradeEntry,
  BagrutRequirement,
  EligibilityResultItem,
  ProgramDetail,
} from '@/types';

// ── localStorage keys ─────────────────────────────────────────────────────────

function storageKey(programId: string, itemIndex: number): string {
  return `roadmap_${programId}_${itemIndex}`;
}

// ── Section A: Requirements status ───────────────────────────────────────────

type RequirementStatus = 'met' | 'improvable' | 'missing';

interface RequirementRow {
  req:         BagrutRequirement;
  status:      RequirementStatus;
  userGrade:   number | null;
  userUnits:   number | null;
  gradeGap:    number | null; // positive → how much to improve grade
  unitsGap:    number | null; // positive → how many more units needed
}

function computeRequirementStatus(
  req: BagrutRequirement,
  grades: BagrutGradeEntry[],
): RequirementRow {
  const entry = grades.find((g) => g.subject === req.subject_code && g.grade !== '');
  if (!entry || entry.grade === '' || entry.units === null) {
    return {
      req, status: 'missing',
      userGrade: null, userUnits: null,
      gradeGap: req.min_grade, unitsGap: req.min_units,
    };
  }

  const grade = entry.grade as number;
  const units = entry.units as number;
  const gradeOk = grade >= req.min_grade;
  const unitsOk = units >= req.min_units;

  if (gradeOk && unitsOk) {
    return {
      req, status: 'met',
      userGrade: grade, userUnits: units,
      gradeGap: null, unitsGap: null,
    };
  }

  // "Improvable" if grade gap ≤ 25 or units gap ≤ 2
  const gradeGap = gradeOk ? null : req.min_grade - grade;
  const unitsGap = unitsOk ? null : req.min_units - units;
  const improvable = (gradeGap !== null && gradeGap <= 25) || (unitsGap !== null && unitsGap <= 2);

  return {
    req,
    status: improvable ? 'improvable' : 'missing',
    userGrade: grade, userUnits: units,
    gradeGap, unitsGap,
  };
}

const STATUS_STYLES: Record<RequirementStatus, { icon: string; color: string; label: string }> = {
  met:        { icon: '✓', color: 'text-eligible-text bg-eligible-bg',        label: 'met'        },
  improvable: { icon: '!', color: 'text-borderline-text bg-borderline-bg',    label: 'improvable' },
  missing:    { icon: '✗', color: 'text-ineligible-text bg-ineligible-bg',    label: 'missing'    },
};

function RequirementStatusIcon({ status }: { status: RequirementStatus }) {
  const s = STATUS_STYLES[status];
  return (
    <span
      aria-hidden="true"
      className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${s.color}`}
    >
      {s.icon}
    </span>
  );
}

function SectionA({ program, grades }: { program: ProgramDetail; grades: BagrutGradeEntry[] }) {
  const t = useTranslations('roadmap.sectionA');
  const tNav = useTranslations('nav');
  const requirements = program.latest_sekem_formula?.bagrut_requirements ?? [];

  if (requirements.length === 0) {
    return (
      <div>
        <h3 className="mb-3 text-base font-semibold text-gray-800">{t('title')}</h3>
        <p className="text-sm text-gray-500">{t('noRequirements')}</p>
      </div>
    );
  }

  if (grades.filter((g) => g.subject !== '').length === 0) {
    return (
      <div>
        <h3 className="mb-3 text-base font-semibold text-gray-800">{t('title')}</h3>
        <p className="mb-3 text-sm text-gray-500">{t('noProfile')}</p>
        <Link
          href="/intake"
          className="inline-block rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          {t('goToIntake')}
        </Link>
      </div>
    );
  }

  const rows = requirements.map((req) => computeRequirementStatus(req, grades));

  return (
    <div>
      <h3 className="mb-3 text-base font-semibold text-gray-800">{t('title')}</h3>
      <ul className="space-y-3">
        {rows.map((row, i) => {
          const s = STATUS_STYLES[row.status];
          return (
            <li
              key={i}
              className="flex items-start gap-3 rounded-lg border border-gray-100 bg-white p-3"
            >
              <RequirementStatusIcon status={row.status} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">
                    {row.req.subject_code}
                  </span>
                  <span className="text-xs text-gray-400">
                    {row.req.mandatory ? t('mandatory') : t('optional')}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap gap-4 text-xs text-gray-600">
                  <span>
                    <span className="font-medium">{t('requiredLabel')}:</span>{' '}
                    {row.req.min_grade}{' '}
                    ({row.req.min_units} יח״ל)
                  </span>
                  {row.userGrade !== null && (
                    <span>
                      <span className="font-medium">{t('yoursLabel')}:</span>{' '}
                      {row.userGrade}{' '}
                      ({row.userUnits} יח״ל)
                    </span>
                  )}
                </div>
                {/* Action hint for improvable */}
                {row.status === 'improvable' && row.gradeGap !== null && (
                  <p className="mt-1 text-xs font-medium text-eligible-text">
                    {t('gradeImprove', { points: row.gradeGap })}
                  </p>
                )}
                {row.status === 'improvable' && row.gradeGap === null && row.unitsGap !== null && (
                  <p className="mt-1 text-xs font-medium text-eligible-text">
                    {t('unitsImprove', { units: row.req.min_units })}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Section B: To-do list ─────────────────────────────────────────────────────

type ItemPriority = 'urgent' | 'medium' | 'parallel';

interface RoadmapItem {
  index:       number;
  priority:    ItemPriority;
  title:       string;
  description: string;
  deadline:    string;
  actionable?: string;
}

const PRIORITY_STYLES: Record<ItemPriority, string> = {
  urgent:   'bg-ineligible-bg   text-ineligible-text',
  medium:   'bg-primary-50      text-primary-800',
  parallel: 'bg-borderline-bg   text-borderline-text',
};

const EARLY_ADMISSION_INSTITUTIONS = new Set([
  'TAU', 'HUJI', 'TECHNION', 'BGU', 'BIU', 'HAIFA', 'ARIEL',
]);

function generateItems(
  program: ProgramDetail,
  resultItem: EligibilityResultItem | undefined,
  allResults: EligibilityResultItem[],
  t: (key: string, params?: Record<string, unknown>) => string,
): RoadmapItem[] {
  const items: RoadmapItem[] = [];
  const formula  = program.latest_sekem_formula;
  const margin   = resultItem?.margin   ?? 0;
  const eligible = resultItem?.eligible ?? false;
  const borderline = resultItem?.borderline ?? false;

  // ── Item 1: Improve psychometric (if not fully eligible) ─────────────────
  if ((!eligible || borderline) && formula && margin < 0) {
    const gap        = -margin;
    const psychoWt   = formula.psychometric_weight;
    const pointsNeeded = psychoWt > 0 ? Math.ceil(gap / psychoWt) : 0;
    items.push({
      priority:    borderline ? 'urgent' : 'medium',
      title:       t('roadmap.items.improvePsycho.title'),
      description: t('roadmap.items.improvePsycho.description', { points: pointsNeeded }),
      deadline:    t('roadmap.items.improvePsycho.deadline'),
      actionable:  pointsNeeded > 0
        ? t('roadmap.sectionA.gradeImprove', { points: pointsNeeded })
        : undefined,
    });
  }

  // ── Item 2: Early admission ───────────────────────────────────────────────
  if (EARLY_ADMISSION_INSTITUTIONS.has(program.institution_id)) {
    items.push({
      priority:    eligible ? 'urgent' : 'medium',
      title:       t('roadmap.items.earlyAdmission.title'),
      description: t('roadmap.items.earlyAdmission.description'),
      deadline:    t('roadmap.items.earlyAdmission.deadline'),
    });
  }

  // ── Item 3: Parallel program (same field, user is already eligible) ────────
  if (!eligible) {
    const parallel = allResults.find(
      (r) => r.program.id !== program.id && r.program.field === program.field && r.eligible
    );
    if (parallel) {
      items.push({
        priority:    'parallel',
        title:       t('roadmap.items.parallelProgram.title', { name: parallel.program.name_he }),
        description: t('roadmap.items.parallelProgram.description', {
          institution: parallel.program.institution.name_he,
          threshold:   parallel.threshold,
        }),
        deadline: t('roadmap.items.parallelProgram.deadline'),
      });
    }
  }

  // ── Last item: Always prepare documents ──────────────────────────────────
  items.push({
    priority:    'medium',
    title:       t('roadmap.items.prepareDocuments.title'),
    description: t('roadmap.items.prepareDocuments.description'),
    deadline:    t('roadmap.items.prepareDocuments.deadline'),
  });

  return items.map((item, index) => ({ ...item, index }));
}

// ── Checkable item component ──────────────────────────────────────────────────

function CheckableItem({
  item,
  programId,
}: {
  item:      RoadmapItem;
  programId: string;
}) {
  const t   = useTranslations('roadmap.sectionB');
  const key = storageKey(programId, item.index);

  const [checked, setChecked] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(key) === 'true';
  });

  const toggle = () => {
    const next = !checked;
    setChecked(next);
    if (typeof window !== 'undefined') {
      if (next) {
        localStorage.setItem(key, 'true');
      } else {
        localStorage.removeItem(key);
      }
    }
  };

  return (
    <li
      className={`flex items-start gap-4 rounded-xl border p-4 transition-colors ${
        checked ? 'border-gray-100 bg-gray-50 opacity-70' : 'border-gray-200 bg-white'
      }`}
    >
      {/* Checkbox */}
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        aria-label={item.title}
        onClick={toggle}
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-colors ${
          checked
            ? 'border-eligible-text bg-eligible-text text-white'
            : 'border-gray-300 bg-white hover:border-primary-400'
        }`}
      >
        {checked && (
          <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
            <path d="M10 3L5 8.5 2 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          </svg>
        )}
      </button>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[item.priority]}`}
          >
            {t(`priorities.${item.priority}`)}
          </span>
          <span
            className={`text-sm font-semibold ${checked ? 'text-gray-400 line-through' : 'text-gray-800'}`}
          >
            {item.title}
          </span>
        </div>

        <p className={`mt-1 text-sm ${checked ? 'text-gray-400' : 'text-gray-600'}`}>
          {item.description}
        </p>

        {item.actionable && !checked && (
          <p className="mt-1 text-xs font-medium text-eligible-text">
            {item.actionable}
          </p>
        )}

        <p className={`mt-1.5 text-xs ${checked ? 'text-gray-400' : 'text-primary-700'}`}>
          {checked ? t('done') + ' ✓' : item.deadline}
        </p>
      </div>
    </li>
  );
}

function SectionB({
  program,
  resultItem,
  allResults,
}: {
  program:     ProgramDetail;
  resultItem:  EligibilityResultItem | undefined;
  allResults:  EligibilityResultItem[];
}) {
  const t     = useTranslations();
  const items = useMemo(
    () => generateItems(program, resultItem, allResults, t),
    [program, resultItem, allResults, t]
  );

  if (!resultItem && !program.latest_sekem_formula) {
    return (
      <div>
        <h3 className="mb-3 text-base font-semibold text-gray-800">
          {t('roadmap.sectionB.title')}
        </h3>
        <p className="text-sm text-gray-500">{t('roadmap.sectionB.noProfile')}</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-3 text-base font-semibold text-gray-800">
        {t('roadmap.sectionB.title')}
      </h3>
      <p className="mb-3 text-xs text-gray-400">{t('roadmap.sectionB.syncHint')}</p>
      <ol className="space-y-3">
        {items.map((item) => (
          <CheckableItem key={item.index} item={item} programId={program.id} />
        ))}
      </ol>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

interface RoadmapSectionProps {
  program: ProgramDetail;
}

export function RoadmapSection({ program }: RoadmapSectionProps) {
  const eligibilityResults = useIntakeStore((s) => s.eligibilityResults);
  const grades             = useIntakeStore((s) => s.bagrutGrades);

  const resultItem = eligibilityResults?.results.find(
    (r) => r.program.id === program.id
  );
  const allResults = eligibilityResults?.results ?? [];

  return (
    <div className="space-y-8">
      <SectionA program={program} grades={grades} />
      <hr className="border-gray-100" />
      <SectionB program={program} resultItem={resultItem} allResults={allResults} />
    </div>
  );
}

// ── localStorage sync utility (called on login) ───────────────────────────────

/**
 * Read all roadmap_* entries from localStorage and return them as a batch
 * payload ready to POST to /api/v1/accounts/me/roadmap-progress.
 *
 * Called by the auth layer after a successful login.
 * After calling this, clear the localStorage keys.
 */
export function drainRoadmapLocalStorage(): Array<{
  program_id: string;
  item_index: number;
  checked: boolean;
  checked_at: string;
}> {
  if (typeof window === 'undefined') return [];
  const items: ReturnType<typeof drainRoadmapLocalStorage> = [];

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key?.startsWith('roadmap_')) continue;
    // Key format: roadmap_{programId}_{itemIndex}
    const parts = key.slice('roadmap_'.length).split('_');
    if (parts.length < 2) continue;
    const itemIndex = Number(parts[parts.length - 1]);
    const programId = parts.slice(0, -1).join('_');
    if (isNaN(itemIndex)) continue;

    items.push({
      program_id: programId,
      item_index: itemIndex,
      checked:    localStorage.getItem(key) === 'true',
      checked_at: new Date().toISOString(),
    });
  }

  return items;
}
