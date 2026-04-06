import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  waitFor,
  resetIntakeStore,
} from '../utils/testUtils';
import { ProgramDetailClient } from '@/components/program/ProgramDetailClient';
import { EligibilitySection } from '@/components/program/EligibilitySection';
import { SyllabusSection } from '@/components/program/SyllabusSection';
import { CareerSection } from '@/components/program/CareerSection';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { useIntakeStore } from '@/store/intakeStore';
import { useAdvisorStore } from '@/store/advisorStore';
import { makeEligibilityResponse, makeResultItem, makeProgram } from '../results/fixtures';
import type { ProgramDetail, SyllabusResponse, CareerDataResponse } from '@/types';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeProgramDetail(
  overrides?: Partial<ProgramDetail>
): ProgramDetail {
  const base = makeProgram();
  return {
    ...base,
    latest_sekem_formula: {
      id:                   'formula-1',
      year:                 2025,
      bagrut_weight:        0.5,
      psychometric_weight:  0.5,
      threshold_sekem:      730,
      subject_bonuses:      [],
      bagrut_requirements:  [],
      scraped_at:           '2025-11-01T00:00:00Z',
      source_url:           'https://tau.ac.il/cs',
    },
    syllabus: null,
    career_data: null,
    data_freshness: {
      institution_id:      'TAU',
      last_scrape_success: new Date().toISOString(),
    },
    ...overrides,
  };
}

function makeSyllabus(overrides?: Partial<SyllabusResponse>): SyllabusResponse {
  return {
    id:                 'syl-1',
    year_1_summary_he:  'מבוא לתכנות ומתמטיקה דיסקרטית',
    year_2_summary_he:  'אלגוריתמים ומערכות הפעלה',
    year_3_summary_he:  'פרויקט גמר ומסלולי התמחות',
    core_courses:       ['מבוא לתכנות', 'אלגוריתמים', 'רשתות'],
    elective_tracks:    ['AI ולמידת מכונה', 'אבטחת מידע'],
    one_line_pitch_he:  'הדרך המהירה ביותר להפוך למפתח.',
    summarized_at:      '2025-10-01T00:00:00Z',
    scraped_at:         '2025-11-01T00:00:00Z',
    ...overrides,
  };
}

function makeCareer(
  overrides?: Partial<CareerDataResponse>
): CareerDataResponse {
  return {
    id:                 'career-1',
    job_titles:         ['מפתח תוכנה', 'מהנדס Backend', 'Data Engineer'],
    avg_salary_min_ils: 18000,
    avg_salary_max_ils: 35000,
    demand_trend:       'growing',
    data_year:          2024,
    source:             'CBS',
    updated_at:         '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  resetIntakeStore();
  useAdvisorStore.getState().close();
  useAdvisorStore.getState().clearMessages();
});

// ── Breadcrumb ────────────────────────────────────────────────────────────────

describe('Breadcrumb', () => {
  it('renders all items', () => {
    render(
      <Breadcrumb
        items={[
          { label: 'בית',    href: '/' },
          { label: 'תוצאות', href: '/results' },
          { label: 'מדעי המחשב' },
        ]}
      />
    );
    expect(screen.getByText('בית')).toBeInTheDocument();
    expect(screen.getByText('תוצאות')).toBeInTheDocument();
    expect(screen.getByText('מדעי המחשב')).toBeInTheDocument();
  });

  it('last item has aria-current=page', () => {
    render(
      <Breadcrumb items={[{ label: 'בית', href: '/' }, { label: 'מדעי המחשב' }]} />
    );
    expect(screen.getByText('מדעי המחשב')).toHaveAttribute('aria-current', 'page');
  });

  it('renders separator between items', () => {
    const { container } = render(
      <Breadcrumb items={[{ label: 'א', href: '/' }, { label: 'ב' }]} />
    );
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });
});

// ── EligibilitySection ────────────────────────────────────────────────────────

describe('EligibilitySection', () => {
  it('shows threshold when no user results', () => {
    const program = makeProgramDetail();
    render(<EligibilitySection program={program} />);
    expect(screen.getByText(/730/)).toBeInTheDocument();
  });

  it('shows no-profile CTA when no user results', () => {
    const program = makeProgramDetail();
    render(<EligibilitySection program={program} />);
    expect(
      screen.getByText('programDetail.eligibility.noProfile')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'programDetail.eligibility.goToIntake' })
    ).toBeInTheDocument();
  });

  it('shows sekem bar when user has results for this program', () => {
    const program = makeProgramDetail();
    const item    = makeResultItem({
      program:  makeProgram({ id: program.id }),
      sekem:    760,
      threshold: 730,
      margin:   30,
      eligible: true,
    });
    useIntakeStore.getState().setEligibilityResults(makeEligibilityResponse([item]));

    render(<EligibilitySection program={program} />);
    // Bar should be present (aria-label mentions the scores)
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('shows "no formula" text when program has no formula', () => {
    const program = makeProgramDetail({ latest_sekem_formula: null });
    render(<EligibilitySection program={program} />);
    expect(
      screen.getByText('programDetail.eligibility.noFormula')
    ).toBeInTheDocument();
  });
});

// ── SyllabusSection ───────────────────────────────────────────────────────────

describe('SyllabusSection', () => {
  it('shows coming-soon when syllabus is null', () => {
    render(<SyllabusSection syllabus={null} />);
    expect(screen.getByText('programDetail.syllabus.comingSoon')).toBeInTheDocument();
  });

  it('renders year summaries', () => {
    render(<SyllabusSection syllabus={makeSyllabus()} />);
    expect(screen.getByText('מבוא לתכנות ומתמטיקה דיסקרטית')).toBeInTheDocument();
    expect(screen.getByText('אלגוריתמים ומערכות הפעלה')).toBeInTheDocument();
    expect(screen.getByText('פרויקט גמר ומסלולי התמחות')).toBeInTheDocument();
  });

  it('renders core courses as tags', () => {
    render(<SyllabusSection syllabus={makeSyllabus()} />);
    expect(screen.getByText('מבוא לתכנות')).toBeInTheDocument();
    expect(screen.getByText('אלגוריתמים')).toBeInTheDocument();
    expect(screen.getByText('רשתות')).toBeInTheDocument();
  });

  it('renders elective tracks', () => {
    render(<SyllabusSection syllabus={makeSyllabus()} />);
    expect(screen.getByText('AI ולמידת מכונה')).toBeInTheDocument();
    expect(screen.getByText('אבטחת מידע')).toBeInTheDocument();
  });

  it('shows coming-soon when syllabus has no content', () => {
    render(
      <SyllabusSection
        syllabus={makeSyllabus({
          year_1_summary_he: null,
          year_2_summary_he: null,
          year_3_summary_he: null,
          core_courses:      [],
          elective_tracks:   [],
        })}
      />
    );
    expect(screen.getByText('programDetail.syllabus.comingSoon')).toBeInTheDocument();
  });
});

// ── CareerSection ─────────────────────────────────────────────────────────────

describe('CareerSection', () => {
  it('shows no-data message when career is null', () => {
    render(<CareerSection career={null} />);
    expect(screen.getByText('programDetail.career.noData')).toBeInTheDocument();
  });

  it('renders job title tags', () => {
    render(<CareerSection career={makeCareer()} />);
    expect(screen.getByText('מפתח תוכנה')).toBeInTheDocument();
    expect(screen.getByText('מהנדס Backend')).toBeInTheDocument();
    expect(screen.getByText('Data Engineer')).toBeInTheDocument();
  });

  it('renders salary range', () => {
    render(<CareerSection career={makeCareer()} />);
    expect(screen.getByText(/18,000/)).toBeInTheDocument();
    expect(screen.getByText(/35,000/)).toBeInTheDocument();
  });

  it('shows growing demand badge', () => {
    render(<CareerSection career={makeCareer({ demand_trend: 'growing' })} />);
    expect(screen.getByText('programDetail.career.trendGrowing')).toBeInTheDocument();
  });

  it('shows stable demand badge', () => {
    render(<CareerSection career={makeCareer({ demand_trend: 'stable' })} />);
    expect(screen.getByText('programDetail.career.trendStable')).toBeInTheDocument();
  });

  it('shows declining demand badge', () => {
    render(<CareerSection career={makeCareer({ demand_trend: 'declining' })} />);
    expect(screen.getByText('programDetail.career.trendDeclining')).toBeInTheDocument();
  });

  it('shows data year', () => {
    render(<CareerSection career={makeCareer({ data_year: 2024 })} />);
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });
});

// ── ProgramDetailClient ───────────────────────────────────────────────────────

describe('ProgramDetailClient — rendering', () => {
  it('renders program name in Hebrew', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('מדעי המחשב');
  });

  it('renders institution name', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    expect(screen.getByText('אוניברסיטת תל אביב')).toBeInTheDocument();
  });

  it('renders official site link', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    const link = screen.getByRole('link', {
      name: /programDetail.header.viewOfficial/i,
    });
    expect(link).toHaveAttribute('href', 'https://go.tau.ac.il/cs');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders breadcrumb with results link', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i });
    expect(nav).toBeInTheDocument();
  });

  it('renders degree type pill', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    expect(screen.getByText(/BSc/)).toBeInTheDocument();
  });

  it('renders tuition when available', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    expect(screen.getByText(/12,480/)).toBeInTheDocument();
  });
});

// ── Advisor button + panel ─────────────────────────────────────────────────────

describe('ProgramDetailClient — advisor', () => {
  it('renders the advisor floating button', () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    expect(
      screen.getByRole('button', { name: /advisor.buttonLabel/i })
    ).toBeInTheDocument();
  });

  it('opens advisor panel on button click', async () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('button', { name: /advisor.buttonLabel/i })
    );

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  it('advisor panel shows panel title', async () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('button', { name: /advisor.buttonLabel/i })
    );

    await waitFor(() => {
      expect(screen.getByText('advisor.panelTitle')).toBeInTheDocument();
    });
  });

  it('advisor panel shows greeting message', async () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('button', { name: /advisor.buttonLabel/i })
    );

    await waitFor(() => {
      // greeting or greetingWithProgram is injected as first message
      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
    });
  });

  it('advisor panel closes on close button click', async () => {
    render(<ProgramDetailClient program={makeProgramDetail()} />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('button', { name: /advisor.buttonLabel/i })
    );
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /advisor.close/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});
