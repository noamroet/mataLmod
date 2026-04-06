import type { EligibilityResultItem, EligibilityResponse } from '@/types';

export function makeProgram(overrides?: Partial<EligibilityResultItem['program']>): EligibilityResultItem['program'] {
  return {
    id:                 crypto.randomUUID(),
    institution_id:     'TAU',
    name_he:            'מדעי המחשב',
    name_en:            'Computer Science',
    field:              'computer_science',
    degree_type:        'BSc',
    duration_years:     3,
    location:           'תל אביב',
    tuition_annual_ils: 12480,
    official_url:       'https://go.tau.ac.il/cs',
    is_active:          true,
    created_at:         '2025-01-01T00:00:00Z',
    updated_at:         '2026-04-01T00:00:00Z',
    institution: {
      id:          'TAU',
      name_he:     'אוניברסיטת תל אביב',
      name_en:     'Tel Aviv University',
      city_he:     'תל אביב',
      city_en:     'Tel Aviv',
      website_url: 'https://tau.ac.il',
    },
    ...overrides,
  };
}

export function makeResultItem(
  overrides?: Partial<EligibilityResultItem>
): EligibilityResultItem {
  const program = makeProgram(overrides?.program);
  return {
    rank:       1,
    program,
    sekem:      740,
    threshold:  730,
    margin:     10,
    eligible:   true,
    borderline: false,
    ...overrides,
    program,
  };
}

export function makeEligibilityResponse(
  items: EligibilityResultItem[] = [makeResultItem()]
): EligibilityResponse {
  return {
    results: items,
    total:   items.length,
    profile_summary: {
      bagrut_average:    90,
      psychometric:      680,
      subject_count:     3,
      has_five_unit_math: true,
    },
  };
}
