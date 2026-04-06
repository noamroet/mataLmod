'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { useIntakeStore } from '@/store/intakeStore';
import type { ProgramDetail, EligibilityResultItem } from '@/types';

// ── Sekem bar ─────────────────────────────────────────────────────────────────

function SekemBar({
  userSekem,
  threshold,
  eligible,
  borderline,
}: {
  userSekem: number;
  threshold: number;
  eligible: boolean;
  borderline: boolean;
}) {
  // Display range: 100 below threshold to 100 above, min 400–900
  const rangeMin = Math.max(threshold - 150, 200);
  const rangeMax = Math.min(threshold + 150, 800);
  const range    = rangeMax - rangeMin;

  const userPct      = Math.min(Math.max(((userSekem - rangeMin) / range) * 100, 2), 98);
  const thresholdPct = Math.min(Math.max(((threshold - rangeMin) / range) * 100, 2), 98);

  const barColor = eligible
    ? 'bg-eligible-bg text-eligible-text'
    : borderline
    ? 'bg-borderline-bg text-borderline-text'
    : 'bg-ineligible-bg text-ineligible-text';

  const fillColor = eligible
    ? 'bg-eligible-text'
    : borderline
    ? 'bg-borderline-text'
    : 'bg-ineligible-text';

  return (
    <div className="space-y-2">
      {/* Bar */}
      <div
        className="relative h-5 w-full rounded-full bg-gray-100"
        role="img"
        aria-label={`ציון ${userSekem} מתוך סף ${threshold}`}
      >
        {/* User fill */}
        <div
          className={`absolute inset-y-0 start-0 rounded-full ${fillColor} opacity-30`}
          style={{ width: `${userPct}%` }}
        />
        {/* Threshold marker */}
        <div
          className="absolute inset-y-0 w-0.5 bg-gray-600"
          style={{ insetInlineStart: `${thresholdPct}%` }}
          aria-hidden="true"
        />
        {/* User score dot */}
        <div
          className={`absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-white shadow ${fillColor}`}
          style={{ insetInlineStart: `calc(${userPct}% - 8px)` }}
          aria-hidden="true"
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs text-gray-500">
        <span>{rangeMin}</span>
        <span>{rangeMax}</span>
      </div>

      {/* Score chips */}
      <div className={`inline-flex flex-wrap gap-3 rounded-lg px-3 py-2 text-sm ${barColor}`}>
        <span>
          <span className="font-medium">הסקם שלך:</span> {userSekem}
        </span>
        <span aria-hidden="true">·</span>
        <span>
          <span className="font-medium">סף קבלה:</span> {threshold}
        </span>
      </div>
    </div>
  );
}

// ── Formula details ────────────────────────────────────────────────────────────

function FormulaDetails({ program }: { program: ProgramDetail }) {
  const t       = useTranslations('programDetail.eligibility');
  const formula = program.latest_sekem_formula;
  if (!formula) return null;

  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-primary-700 hover:underline">
        {t('formula', { year: formula.year })}
      </summary>
      <div className="mt-2 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
        <dl className="space-y-1 text-gray-700">
          <div className="flex gap-2">
            <dt className="font-medium">{t('bagrutWeight')}:</dt>
            <dd>{(formula.bagrut_weight * 100).toFixed(0)}%</dd>
          </div>
          <div className="flex gap-2">
            <dt className="font-medium">{t('psychoWeight')}:</dt>
            <dd>{(formula.psychometric_weight * 100).toFixed(0)}%</dd>
          </div>
        </dl>
      </div>
    </details>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function EligibilitySection({ program }: { program: ProgramDetail }) {
  const t       = useTranslations('programDetail.eligibility');
  const results = useIntakeStore((s) => s.eligibilityResults);

  // Find this program in the user's results
  const resultItem: EligibilityResultItem | undefined = results?.results.find(
    (r) => r.program.id === program.id
  );

  const threshold = program.latest_sekem_formula?.threshold_sekem ?? null;

  return (
    <section aria-labelledby="eligibility-title" className="space-y-4">
      <h2 id="eligibility-title" className="text-lg font-bold text-gray-900">
        {t('title')}
      </h2>

      {resultItem ? (
        /* User has run eligibility check — show personalised bar */
        <div className="space-y-3">
          <SekemBar
            userSekem={resultItem.sekem}
            threshold={resultItem.threshold}
            eligible={resultItem.eligible}
            borderline={resultItem.borderline}
          />
          <FormulaDetails program={program} />
        </div>
      ) : threshold ? (
        /* No personal data — show threshold only */
        <div className="space-y-3">
          <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
            <span className="font-medium">{t('threshold')}:</span>{' '}
            <strong className="text-gray-900">{threshold}</strong>
          </div>
          <p className="text-sm text-gray-500">{t('noProfile')}</p>
          <Link
            href="/intake"
            className="inline-block rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            {t('goToIntake')}
          </Link>
          <FormulaDetails program={program} />
        </div>
      ) : (
        /* No formula in DB yet */
        <p className="text-sm text-gray-500">{t('noFormula')}</p>
      )}
    </section>
  );
}
