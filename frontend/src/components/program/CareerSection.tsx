import { useTranslations } from 'next-intl';
import type { CareerDataResponse } from '@/types';

function DemandBadge({ trend }: { trend: CareerDataResponse['demand_trend'] }) {
  const t = useTranslations('programDetail.career');

  const styles = {
    growing:   'bg-eligible-bg   text-eligible-text',
    stable:    'bg-primary-50    text-primary-800',
    declining: 'bg-borderline-bg text-borderline-text',
  } as const;

  const labels = {
    growing:   t('trendGrowing'),
    stable:    t('trendStable'),
    declining: t('trendDeclining'),
  } as const;

  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${styles[trend]}`}>
      {labels[trend]}
    </span>
  );
}

function JobTag({ label }: { label: string }) {
  return (
    <span className="inline-block rounded-full bg-primary-50 px-3 py-1 text-xs text-primary-800">
      {label}
    </span>
  );
}

function SalaryDisplay({ career }: { career: CareerDataResponse }) {
  const t = useTranslations('programDetail.career');

  if (career.avg_salary_min_ils && career.avg_salary_max_ils) {
    return (
      <span className="text-sm font-medium text-gray-800">
        {t('salaryRange', {
          min: career.avg_salary_min_ils.toLocaleString('he-IL'),
          max: career.avg_salary_max_ils.toLocaleString('he-IL'),
        })}
      </span>
    );
  }
  if (career.avg_salary_min_ils) {
    return (
      <span className="text-sm font-medium text-gray-800">
        {t('salaryMinOnly', {
          min: career.avg_salary_min_ils.toLocaleString('he-IL'),
        })}
      </span>
    );
  }
  return <span className="text-sm text-gray-500">{t('noSalary')}</span>;
}

interface CareerSectionProps {
  career: CareerDataResponse | null;
}

export function CareerSection({ career }: CareerSectionProps) {
  const t = useTranslations('programDetail.career');

  return (
    <section aria-labelledby="career-title" className="space-y-4">
      <h2 id="career-title" className="text-lg font-bold text-gray-900">
        {t('title')}
      </h2>

      {!career ? (
        <p className="text-sm text-gray-500">{t('noData')}</p>
      ) : (
        <div className="space-y-4">
          {/* Job titles */}
          {career.job_titles.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium text-gray-700">{t('jobTitles')}</p>
              <div className="flex flex-wrap gap-2">
                {career.job_titles.map((title) => (
                  <JobTag key={title} label={title} />
                ))}
              </div>
            </div>
          )}

          {/* Salary + demand row */}
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
                {t('salary')}
              </dt>
              <dd className="mt-1">
                <SalaryDisplay career={career} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
                {t('demandTrend')}
              </dt>
              <dd className="mt-1">
                <DemandBadge trend={career.demand_trend} />
              </dd>
            </div>
          </dl>

          <p className="text-xs text-gray-400">{t('dataYear', { year: career.data_year })}</p>
        </div>
      )}
    </section>
  );
}
