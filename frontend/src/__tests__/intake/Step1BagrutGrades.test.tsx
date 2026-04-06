import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  within,
  waitFor,
  resetIntakeStore,
} from '../utils/testUtils';
import { Step1BagrutGrades } from '@/components/intake/Step1BagrutGrades';
import { weightedBagrutAverage } from '@/store/intakeStore';
import type { BagrutGradeEntry } from '@/types';

beforeEach(() => {
  resetIntakeStore();
});

// ── Weighted average calculation ──────────────────────────────────────────────

describe('weightedBagrutAverage', () => {
  const entry = (units: 3 | 4 | 5, grade: number): BagrutGradeEntry => ({
    id: 'x',
    subject: 'math',
    units,
    grade,
  });

  it('returns 0 for empty list', () => {
    expect(weightedBagrutAverage([])).toBe(0);
  });

  it('returns grade for single 4-unit subject', () => {
    expect(weightedBagrutAverage([entry(4, 90)])).toBe(90);
  });

  it('returns grade for single 3-unit subject', () => {
    expect(weightedBagrutAverage([entry(3, 80)])).toBe(80);
  });

  it('applies 5-unit ×1.25 bonus correctly', () => {
    // One 5-unit subject at 100: weight = 5 × 1.25 = 6.25; avg = 100
    expect(weightedBagrutAverage([entry(5, 100)])).toBe(100);
  });

  it('gives 5-unit subject higher weight than 4-unit subject', () => {
    // 5-unit at 100 (weight 6.25) vs 4-unit at 0 (weight 4): avg = 625/10.25 ≈ 60.97
    const avg = weightedBagrutAverage([entry(5, 100), entry(4, 0)]);
    expect(avg).toBeCloseTo(60.975, 1);
  });

  it('ignores incomplete rows (grade empty)', () => {
    const incomplete: BagrutGradeEntry = {
      id: 'y',
      subject: 'english',
      units: 4,
      grade: '',
    };
    expect(weightedBagrutAverage([incomplete, entry(4, 80)])).toBe(80);
  });

  it('matches known TAU CS example', () => {
    // math 5u 90 + english 4u 85 + physics 5u 88
    // weights: 5×1.25=6.25, 4×1=4, 5×1.25=6.25 | totalW=16.5
    // weighted: 90×6.25 + 85×4 + 88×6.25 = 562.5 + 340 + 550 = 1452.5
    // avg = 1452.5 / 16.5 ≈ 88.03
    const grades = [entry(5, 90), { ...entry(4, 85), subject: 'english', id: 'e' }, { ...entry(5, 88), subject: 'physics', id: 'p' }];
    expect(weightedBagrutAverage(grades)).toBeCloseTo(88.03, 1);
  });
});

// ── UI behaviour ──────────────────────────────────────────────────────────────

describe('Step1BagrutGrades — UI', () => {
  it('renders with one empty row by default', () => {
    render(<Step1BagrutGrades errors={{}} />);
    // One grade input
    expect(screen.getAllByPlaceholderText('intake.step1.gradePlaceholder')).toHaveLength(1);
  });

  it('"Add subject" button adds another row', async () => {
    render(<Step1BagrutGrades errors={{}} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /intake.step1.addSubject/i }));

    expect(
      screen.getAllByPlaceholderText('intake.step1.gradePlaceholder')
    ).toHaveLength(2);
  });

  it('remove button removes a row (visible only when > 1 row)', async () => {
    render(<Step1BagrutGrades errors={{}} />);
    const user = userEvent.setup();

    // Add a row first
    await user.click(screen.getByRole('button', { name: /intake.step1.addSubject/i }));
    expect(screen.getAllByPlaceholderText('intake.step1.gradePlaceholder')).toHaveLength(2);

    // Remove button should now be visible
    const removeBtns = screen.getAllByRole('button', {
      name: /intake.step1.removeSubject/i,
    });
    expect(removeBtns.length).toBeGreaterThan(0);
    await user.click(removeBtns[0]);

    expect(
      screen.getAllByPlaceholderText('intake.step1.gradePlaceholder')
    ).toHaveLength(1);
  });

  it('weighted average is displayed live as grade is typed', async () => {
    render(<Step1BagrutGrades errors={{}} />);
    const user = userEvent.setup();

    // Set units
    const selects = document.querySelectorAll('select');
    await user.selectOptions(selects[0] as HTMLSelectElement, '4');

    // Type a grade
    const gradeInput = screen.getByPlaceholderText('intake.step1.gradePlaceholder');
    await user.type(gradeInput, '90');

    await waitFor(() => {
      // The average display should update (aria-live region)
      expect(screen.getByText(/90/)).toBeInTheDocument();
    });
  });

  it('shows estimated average input when checkbox is checked', async () => {
    render(<Step1BagrutGrades errors={{}} />);
    const user = userEvent.setup();

    const checkbox = screen.getByRole('checkbox', {
      name: /intake.step1.estimatedCheckbox/i,
    });
    await user.click(checkbox);

    expect(
      screen.getByPlaceholderText('intake.step1.estimatedPlaceholder')
    ).toBeInTheDocument();
    // Regular subject rows should be gone
    expect(
      screen.queryByPlaceholderText('intake.step1.gradePlaceholder')
    ).not.toBeInTheDocument();
  });

  it('grade input validation: shows error for grade > 100', async () => {
    render(
      <Step1BagrutGrades
        errors={{
          grades: {
            // The initial row id is unknown — render with known id via store
          },
        }}
      />
    );
    // Inject error via props
    const storeState = (await import('@/store/intakeStore')).useIntakeStore.getState();
    const rowId = storeState.bagrutGrades[0].id;
    render(
      <Step1BagrutGrades
        errors={{ grades: { [rowId]: { grade: 'intake.step1.validation.gradeRange' } } }}
      />
    );
    expect(
      screen.getByText('intake.step1.validation.gradeRange')
    ).toBeInTheDocument();
  });

  it('shows general error when no subjects are added', () => {
    render(
      <Step1BagrutGrades
        errors={{ general: 'intake.step1.validation.atLeastOne' }}
      />
    );
    expect(
      screen.getByText('intake.step1.validation.atLeastOne')
    ).toBeInTheDocument();
  });
});
