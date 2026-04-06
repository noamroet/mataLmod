// ── API request / response types (mirror backend Pydantic schemas) ────────────

export interface BagrutGradeApi {
  subject_code: string;
  units: 3 | 4 | 5;
  grade: number;
}

export interface Preferences {
  fields: string[];
  locations: string[];
  degree_types: string[];
  institution_ids: string[];
}

export interface EligibilityRequest {
  bagrut_grades: BagrutGradeApi[];
  psychometric: number | null;
  preferences: Preferences;
}

export interface InstitutionResponse {
  id: string;
  name_he: string;
  name_en: string;
  city_he: string;
  city_en: string;
  website_url: string;
}

export interface ProgramListItem {
  id: string;
  institution_id: string;
  name_he: string;
  name_en: string | null;
  field: string;
  degree_type: string;
  duration_years: number;
  location: string;
  tuition_annual_ils: number | null;
  official_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  institution: InstitutionResponse;
}

export interface ProfileSummary {
  bagrut_average: number;
  psychometric: number | null;
  subject_count: number;
  has_five_unit_math: boolean;
}

export interface EligibilityResultItem {
  rank: number;
  program: ProgramListItem;
  sekem: number;
  threshold: number;
  margin: number;
  eligible: boolean;
  borderline: boolean;
}

export interface EligibilityResponse {
  results: EligibilityResultItem[];
  total: number;
  profile_summary: ProfileSummary;
}

// ── Program detail ─────────────────────────────────────────────────────────────

export interface SekemFormulaResponse {
  id: string;
  year: number;
  bagrut_weight: number;
  psychometric_weight: number;
  threshold_sekem: number;
  subject_bonuses: SubjectBonus[];
  bagrut_requirements: BagrutRequirement[];
  scraped_at: string;
  source_url: string;
}

export interface SubjectBonus {
  subject_code: string;
  units: number;
  bonus_points: number;
}

export interface BagrutRequirement {
  subject_code: string;
  min_units: number;
  min_grade: number;
  mandatory: boolean;
}

export interface SyllabusResponse {
  id: string;
  year_1_summary_he: string | null;
  year_2_summary_he: string | null;
  year_3_summary_he: string | null;
  core_courses: string[];
  elective_tracks: string[];
  one_line_pitch_he: string | null;
  summarized_at: string | null;
  scraped_at: string;
}

export interface CareerDataResponse {
  id: string;
  job_titles: string[];
  avg_salary_min_ils: number | null;
  avg_salary_max_ils: number | null;
  demand_trend: 'growing' | 'stable' | 'declining';
  data_year: number;
  source: string;
  updated_at: string;
}

export interface DataFreshness {
  institution_id: string;
  last_scrape_success: string | null;
}

export interface ProgramDetail extends ProgramListItem {
  latest_sekem_formula: SekemFormulaResponse | null;
  syllabus: SyllabusResponse | null;
  career_data: CareerDataResponse | null;
  data_freshness: DataFreshness;
}

// ── Advisor ────────────────────────────────────────────────────────────────────

export interface AdvisorMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AdvisorChatRequest {
  message: string;
  user_profile: {
    bagrut_grades: BagrutGradeApi[];
    psychometric: number | null;
  };
  current_program_id: string | null;
  conversation_history: AdvisorMessage[];
}

// ── Store-side intake types (richer than API types) ───────────────────────────

export interface BagrutGradeEntry {
  id: string;      // local uuid for React key
  subject: string; // subject_code or '' if not yet chosen
  units: 3 | 4 | 5 | null;
  grade: number | '';
}

export type LocationFilter = 'all' | 'north' | 'center' | 'south' | 'jerusalem';
export type InstitutionTypeFilter = 'universities' | 'all';
export type StudyFormatFilter = 'full_time' | 'part_time' | 'any';

// ── Constants ─────────────────────────────────────────────────────────────────

export const SUBJECT_CODES = [
  'math',
  'english',
  'hebrew_expression',
  'bible',
  'history',
  'civics',
  'physics',
  'chemistry',
  'biology',
  'computer_science',
  'literature',
  'art',
  'music',
  'economics',
  'accounting',
  'other',
] as const;

export type SubjectCode = (typeof SUBJECT_CODES)[number];

export const FIELD_CODES = [
  'computer_science',
  'electrical_engineering',
  'mechanical_engineering',
  'civil_engineering',
  'biomedical',
  'mathematics',
  'physics_chemistry',
  'medicine',
  'law',
  'business',
  'psychology',
  'education',
  'humanities',
  'arts_design',
  'communication',
  'agriculture',
  'other',
] as const;

export type FieldCode = (typeof FIELD_CODES)[number];

// Location → Hebrew city names sent to backend
export const LOCATION_TO_CITIES: Record<LocationFilter, string[]> = {
  all:       [],
  north:     ['חיפה'],
  center:    ['תל אביב', 'רמת גן', 'אריאל'],
  south:     ['באר שבע'],
  jerusalem: ['ירושלים'],
};
