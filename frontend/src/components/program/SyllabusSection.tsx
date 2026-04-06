import { useTranslations } from 'next-intl';
import type { SyllabusResponse } from '@/types';

function CourseTag({ label }: { label: string }) {
  return (
    <span className="inline-block rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">
      {label}
    </span>
  );
}

function YearSummary({ year, text }: { year: number; text: string }) {
  const t = useTranslations('programDetail.syllabus');
  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold text-gray-700">
        {t('year', { n: year })}
      </h3>
      <p className="text-sm leading-relaxed text-gray-600">{text}</p>
    </div>
  );
}

interface SyllabusSectionProps {
  syllabus: SyllabusResponse | null;
}

export function SyllabusSection({ syllabus }: SyllabusSectionProps) {
  const t = useTranslations('programDetail.syllabus');

  const hasYearContent =
    syllabus?.year_1_summary_he ||
    syllabus?.year_2_summary_he ||
    syllabus?.year_3_summary_he;

  const hasCourses =
    (syllabus?.core_courses?.length ?? 0) > 0 ||
    (syllabus?.elective_tracks?.length ?? 0) > 0;

  return (
    <section aria-labelledby="syllabus-title" className="space-y-4">
      <h2 id="syllabus-title" className="text-lg font-bold text-gray-900">
        {t('title')}
      </h2>

      {!syllabus || (!hasYearContent && !hasCourses) ? (
        <p className="text-sm text-gray-500">{t('comingSoon')}</p>
      ) : (
        <div className="space-y-5">
          {/* Year-by-year summaries */}
          {hasYearContent && (
            <div className="space-y-4">
              {syllabus.year_1_summary_he && (
                <YearSummary year={1} text={syllabus.year_1_summary_he} />
              )}
              {syllabus.year_2_summary_he && (
                <YearSummary year={2} text={syllabus.year_2_summary_he} />
              )}
              {syllabus.year_3_summary_he && (
                <YearSummary year={3} text={syllabus.year_3_summary_he} />
              )}
            </div>
          )}

          {/* Core courses */}
          {(syllabus.core_courses?.length ?? 0) > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-gray-700">
                {t('coreCourses')}
              </h3>
              <div className="flex flex-wrap gap-2">
                {syllabus.core_courses.map((course) => (
                  <CourseTag key={course} label={course} />
                ))}
              </div>
            </div>
          )}

          {/* Elective tracks */}
          {(syllabus.elective_tracks?.length ?? 0) > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-gray-700">
                {t('electiveTracks')}
              </h3>
              <div className="flex flex-wrap gap-2">
                {syllabus.elective_tracks.map((track) => (
                  <CourseTag key={track} label={track} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
