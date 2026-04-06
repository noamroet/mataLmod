import type {
  BagrutGradeEntry,
  BagrutGradeApi,
  EligibilityRequest,
  LocationFilter,
  InstitutionTypeFilter,
  LOCATION_TO_CITIES,
  FieldCode,
} from '@/types';
import { LOCATION_TO_CITIES as LOC_MAP } from '@/types';

/** Build the API request payload from the Zustand store state. */
export function buildEligibilityRequest(params: {
  bagrutGrades: BagrutGradeEntry[];
  useEstimatedAverage: boolean;
  estimatedAverage: number | '';
  psychometricScore: number | '';
  haventTakenPsychometric: boolean;
  fieldsOfInterest: FieldCode[];
  location: LocationFilter;
  institutionType: InstitutionTypeFilter;
}): EligibilityRequest {
  const {
    bagrutGrades,
    useEstimatedAverage,
    estimatedAverage,
    psychometricScore,
    haventTakenPsychometric,
    fieldsOfInterest,
    location,
  } = params;

  // Convert grade entries to API format
  let bagrutApiGrades: BagrutGradeApi[];
  if (useEstimatedAverage) {
    // Represent estimated average as a single 4-unit "other" subject
    // The sekem engine will treat it as the weighted average directly.
    // We send a synthetic single grade so the backend calculation works.
    const avg = typeof estimatedAverage === 'number' ? estimatedAverage : 0;
    bagrutApiGrades = [{ subject_code: 'other', units: 4, grade: avg }];
  } else {
    bagrutApiGrades = bagrutGrades
      .filter(
        (g): g is BagrutGradeEntry & { subject: string; units: 3 | 4 | 5; grade: number } =>
          g.subject !== '' && g.units !== null && g.grade !== ''
      )
      .map((g) => ({
        subject_code: g.subject,
        units:        g.units,
        grade:        g.grade,
      }));
  }

  const psychometric =
    haventTakenPsychometric || psychometricScore === ''
      ? null
      : (psychometricScore as number);

  return {
    bagrut_grades: bagrutApiGrades,
    psychometric,
    preferences: {
      fields:          fieldsOfInterest,
      locations:       LOC_MAP[location],
      degree_types:    [],
      institution_ids: [],
    },
  };
}

/** Format a number as Israeli Shekel (₪). */
export function formatILS(amount: number): string {
  return new Intl.NumberFormat('he-IL', {
    style:    'currency',
    currency: 'ILS',
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Clamp a value between min and max. */
export function clamp(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), max);
}

/** Round to at most 2 decimal places, dropping trailing zeros. */
export function roundDisplay(v: number): string {
  return Number(v.toFixed(2)).toString();
}
