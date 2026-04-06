import userEvent from '@testing-library/user-event';
import { render, screen, resetIntakeStore } from '../utils/testUtils';
import { CompareClient } from '@/components/compare/CompareClient';
import { useComparisonStore } from '@/store/comparisonStore';
import { useIntakeStore }     from '@/store/intakeStore';
import { makeEligibilityResponse, makeResultItem, makeProgram } from '../results/fixtures';
import type { ProgramDetail, SyllabusResponse, CareerDataResponse } from '@/types';

// ── API mock ──────────────────────────────────────────────────────────────────

jest.mock('@/lib/api', () => ({
  fetchProgram: jest.fn(),
}));

import { fetchProgram } from '@/lib/api';
const mockFetchProgram = fetchProgram as jest.MockedFunction<typeof fetchProgram>;

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeProgramDetail(overrides?: Partial<ProgramDetail>): ProgramDetail {
  const base = makeProgram();
  return {
    ...base,
    latest_sekem_formula: {
      id:                  'formula-1',
      year:                2025,
      bagrut_weight:       0.5,
      psychometric_weight: 0.5,
      threshold_sekem:     730,
      subject_bonuses:     [],
      bagrut_requirements: [],
      scraped_at:          '2025-11-01T00:00:00Z',
      source_url:          'https://tau.ac.il/cs',
    },
    syllabus:     null,
    career_data:  null,
    data_freshness: {
      institution_id:      'TAU',
      last_scrape_success: new Date().toISOString(),
    },
    ...overrides,
  };
}

function makeSyllabus(overrides?: Partial<SyllabusResponse>): SyllabusResponse {
  return {
    id:                'syl-1',
    year_1_summary_he: 'מבוא לתכנות',
    year_2_summary_he: 'אלגוריתמים',
    year_3_summary_he: 'פרויקט גמר',
    core_courses:      ['מבוא לתכנות', 'אלגוריתמים'],
    elective_tracks:   ['AI'],
    one_line_pitch_he: 'תואר מהיר למפתחים',
    summarized_at:     '2025-10-01T00:00:00Z',
    scraped_at:        '2025-11-01T00:00:00Z',
    ...overrides,
  };
}

function makeCareer(overrides?: Partial<CareerDataResponse>): CareerDataResponse {
  return {
    id:                  'career-1',
    job_titles:          ['מפתח תוכנה', 'Backend Engineer'],
    avg_salary_min_ils:  18000,
    avg_salary_max_ils:  35000,
    demand_trend:        'growing',
    data_year:           2024,
    source:              'CBS',
    updated_at:          '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  resetIntakeStore();
  useComparisonStore.getState().clearComparison();
  mockFetchProgram.mockReset();
});

// ── Empty state ───────────────────────────────────────────────────────────────

describe('CompareClient — empty state', () => {
  it('shows empty state when no programs selected', () => {
    render(<CompareClient />);
    expect(
      screen.getByText('compare.empty.title')
    ).toBeInTheDocument();
  });

  it('shows CTA link to results', () => {
    render(<CompareClient />);
    expect(
      screen.getByRole('link', { name: 'compare.empty.cta' })
    ).toHaveAttribute('href', '/results');
  });
});

// ── Loading state ─────────────────────────────────────────────────────────────

describe('CompareClient — loading', () => {
  it('shows skeleton while loading', () => {
    // fetchProgram never resolves during this test
    mockFetchProgram.mockImplementation(() => new Promise(() => {}));
    useComparisonStore.getState().addProgram('prog-1');

    const { container } = render(<CompareClient />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });
});

// ── Single program comparison ─────────────────────────────────────────────────

describe('CompareClient — single program', () => {
  let program: ProgramDetail;

  beforeEach(() => {
    program = makeProgramDetail({ id: 'prog-1' });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');
  });

  it('renders the compare page heading', async () => {
    render(<CompareClient />);
    expect(
      await screen.findByText('compare.title')
    ).toBeInTheDocument();
  });

  it('renders program name in header', async () => {
    render(<CompareClient />);
    expect(await screen.findByText('מדעי המחשב')).toBeInTheDocument();
  });

  it('renders institution name in header', async () => {
    render(<CompareClient />);
    expect(await screen.findByText('אוניברסיטת תל אביב')).toBeInTheDocument();
  });

  it('renders link back to results', async () => {
    render(<CompareClient />);
    await screen.findByText('compare.title'); // wait for load
    expect(
      screen.getByRole('link', { name: /compare.backToResults/ })
    ).toHaveAttribute('href', '/results');
  });

  it('renders "view program" link', async () => {
    render(<CompareClient />);
    const link = await screen.findByRole('link', { name: /compare.viewProgram/ });
    expect(link).toHaveAttribute('href', `/program/${program.id}`);
  });

  it('renders remove button', async () => {
    render(<CompareClient />);
    expect(
      await screen.findByRole('button', { name: 'compare.removeProgram' })
    ).toBeInTheDocument();
  });

  it('removes program when remove button clicked', async () => {
    const user = userEvent.setup();
    render(<CompareClient />);
    const btn = await screen.findByRole('button', { name: 'compare.removeProgram' });
    await user.click(btn);
    expect(useComparisonStore.getState().selectedIds).toHaveLength(0);
  });

  it('shows threshold row with year', async () => {
    render(<CompareClient />);
    await screen.findByText('compare.title');
    // threshold cell: "compare.values.threshold" interpolated with value and year
    expect(screen.getByText(/730/)).toBeInTheDocument();
    expect(screen.getByText(/2025/)).toBeInTheDocument();
  });

  it('shows no-sekem placeholder when no eligibility results', async () => {
    render(<CompareClient />);
    await screen.findByText('compare.title');
    // yourSekem row shows noSekem placeholder
    expect(screen.getAllByText('compare.values.noSekem').length).toBeGreaterThan(0);
  });

  it('shows degree type row', async () => {
    render(<CompareClient />);
    await screen.findByText('BSc');
  });

  it('shows location row', async () => {
    render(<CompareClient />);
    await screen.findByText('תל אביב');
  });

  it('shows tuition row when available', async () => {
    render(<CompareClient />);
    await screen.findByText(/12,480/);
  });

  it('shows no-salary placeholder when no career data', async () => {
    render(<CompareClient />);
    await screen.findByText('compare.title');
    expect(screen.getByText('compare.values.noSalary')).toBeInTheDocument();
  });

  it('shows no-pitch placeholder when syllabus is null', async () => {
    render(<CompareClient />);
    await screen.findByText('compare.title');
    expect(screen.getByText('compare.values.noPitch')).toBeInTheDocument();
  });
});

// ── Eligibility data from intake store ───────────────────────────────────────

describe('CompareClient — with eligibility results', () => {
  it('shows user sekem from intake store', async () => {
    const program = makeProgramDetail({ id: 'prog-1' });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');

    const resultItem = makeResultItem({
      program:   makeProgram({ id: 'prog-1' }),
      sekem:     755,
      threshold: 730,
      margin:    25,
      eligible:  true,
    });
    useIntakeStore.getState().setEligibilityResults(makeEligibilityResponse([resultItem]));

    render(<CompareClient />);
    await screen.findByText('compare.title');
    expect(screen.getByText('755.0')).toBeInTheDocument();
  });

  it('shows positive margin in eligible color', async () => {
    const program = makeProgramDetail({ id: 'prog-1' });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');

    const resultItem = makeResultItem({
      program:   makeProgram({ id: 'prog-1' }),
      sekem:     755,
      threshold: 730,
      margin:    25,
      eligible:  true,
    });
    useIntakeStore.getState().setEligibilityResults(makeEligibilityResponse([resultItem]));

    render(<CompareClient />);
    await screen.findByText('compare.title');
    // margin formatted as "+25"
    expect(screen.getByText(/\+25/)).toBeInTheDocument();
  });

  it('shows eligible badge', async () => {
    const program = makeProgramDetail({ id: 'prog-1' });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');

    const resultItem = makeResultItem({
      program:   makeProgram({ id: 'prog-1' }),
      eligible:  true,
      borderline: false,
    });
    useIntakeStore.getState().setEligibilityResults(makeEligibilityResponse([resultItem]));

    render(<CompareClient />);
    await screen.findByText('compare.eligibilityStatus.eligible');
  });

  it('shows borderline badge', async () => {
    const program = makeProgramDetail({ id: 'prog-1' });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');

    const resultItem = makeResultItem({
      program:    makeProgram({ id: 'prog-1' }),
      eligible:   false,
      borderline: true,
    });
    useIntakeStore.getState().setEligibilityResults(makeEligibilityResponse([resultItem]));

    render(<CompareClient />);
    await screen.findByText('compare.eligibilityStatus.borderline');
  });
});

// ── Career data ───────────────────────────────────────────────────────────────

describe('CompareClient — career data', () => {
  beforeEach(() => {
    useComparisonStore.getState().addProgram('prog-1');
  });

  it('renders salary range', async () => {
    const program = makeProgramDetail({
      id:          'prog-1',
      career_data: makeCareer(),
    });
    mockFetchProgram.mockResolvedValue(program);
    render(<CompareClient />);
    await screen.findByText('compare.title');
    expect(screen.getByText(/18,000/)).toBeInTheDocument();
    expect(screen.getByText(/35,000/)).toBeInTheDocument();
  });

  it('renders growing demand badge', async () => {
    const program = makeProgramDetail({
      id:          'prog-1',
      career_data: makeCareer({ demand_trend: 'growing' }),
    });
    mockFetchProgram.mockResolvedValue(program);
    render(<CompareClient />);
    await screen.findByText('compare.demand.growing');
  });

  it('renders stable demand badge', async () => {
    const program = makeProgramDetail({
      id:          'prog-1',
      career_data: makeCareer({ demand_trend: 'stable' }),
    });
    mockFetchProgram.mockResolvedValue(program);
    render(<CompareClient />);
    await screen.findByText('compare.demand.stable');
  });

  it('renders job titles (up to 3)', async () => {
    const program = makeProgramDetail({
      id:          'prog-1',
      career_data: makeCareer({ job_titles: ['תפקיד א', 'תפקיד ב', 'תפקיד ג', 'תפקיד ד'] }),
    });
    mockFetchProgram.mockResolvedValue(program);
    render(<CompareClient />);
    await screen.findByText('compare.title');
    expect(screen.getByText('תפקיד א')).toBeInTheDocument();
    expect(screen.getByText('תפקיד ב')).toBeInTheDocument();
    expect(screen.getByText('תפקיד ג')).toBeInTheDocument();
    expect(screen.queryByText('תפקיד ד')).not.toBeInTheDocument(); // 4th clipped
  });
});

// ── Curriculum / pitch ────────────────────────────────────────────────────────

describe('CompareClient — curriculum pitch', () => {
  it('renders one-line pitch when available', async () => {
    const program = makeProgramDetail({
      id:       'prog-1',
      syllabus: makeSyllabus({ one_line_pitch_he: 'תואר מהיר למפתחים' }),
    });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');
    render(<CompareClient />);
    await screen.findByText('תואר מהיר למפתחים');
  });

  it('renders no-pitch placeholder when syllabus has no pitch', async () => {
    const program = makeProgramDetail({
      id:       'prog-1',
      syllabus: makeSyllabus({ one_line_pitch_he: null }),
    });
    mockFetchProgram.mockResolvedValue(program);
    useComparisonStore.getState().addProgram('prog-1');
    render(<CompareClient />);
    await screen.findByText('compare.title');
    expect(screen.getByText('compare.values.noPitch')).toBeInTheDocument();
  });
});

// ── Multi-program comparison ──────────────────────────────────────────────────

describe('CompareClient — multiple programs', () => {
  it('renders two program headers side by side', async () => {
    const prog1 = makeProgramDetail({ id: 'prog-1', name_he: 'מדעי המחשב' });
    const prog2 = makeProgramDetail({
      id:         'prog-2',
      name_he:    'הנדסת חשמל',
      field:      'electrical_engineering',
      degree_type: 'BSc',
    });

    mockFetchProgram.mockImplementation((id) =>
      id === 'prog-1' ? Promise.resolve(prog1) : Promise.resolve(prog2)
    );

    useComparisonStore.getState().addProgram('prog-1');
    useComparisonStore.getState().addProgram('prog-2');

    render(<CompareClient />);

    expect(await screen.findByText('מדעי המחשב')).toBeInTheDocument();
    expect(await screen.findByText('הנדסת חשמל')).toBeInTheDocument();
  });

  it('renders two remove buttons', async () => {
    const prog1 = makeProgramDetail({ id: 'prog-1' });
    const prog2 = makeProgramDetail({ id: 'prog-2' });

    mockFetchProgram.mockImplementation((id) =>
      id === 'prog-1' ? Promise.resolve(prog1) : Promise.resolve(prog2)
    );

    useComparisonStore.getState().addProgram('prog-1');
    useComparisonStore.getState().addProgram('prog-2');

    render(<CompareClient />);
    await screen.findByText('compare.title');

    expect(
      screen.getAllByRole('button', { name: 'compare.removeProgram' })
    ).toHaveLength(2);
  });
});
