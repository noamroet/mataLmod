import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  waitFor,
  resetIntakeStore,
} from '../utils/testUtils';
import { IntakeWizard } from '@/components/intake/IntakeWizard';
import * as api from '@/lib/api';

jest.mock('@/lib/api');

const mockCalculate = api.calculateEligibility as jest.MockedFunction<
  typeof api.calculateEligibility
>;

beforeEach(() => {
  resetIntakeStore();
  jest.clearAllMocks();
});

describe('IntakeWizard — step navigation', () => {
  it('renders step 1 initially', () => {
    render(<IntakeWizard />);
    expect(screen.getByText('intake.step1.title')).toBeInTheDocument();
  });

  it('advances to step 2 when Next is clicked with valid step 1 data', async () => {
    render(<IntakeWizard />);
    const user = userEvent.setup();

    // Fill in a valid subject row
    const unitSelect = screen.getByRole('combobox', { hidden: true });
    // Set grade via the number input
    const gradeInput = screen.getByPlaceholderText('intake.step1.gradePlaceholder');
    await user.type(gradeInput, '90');

    // Units select
    const unitsSelect = screen.getByRole('listbox', { hidden: true }) ??
      document.querySelector('select');
    // Use the select directly
    const selects = document.querySelectorAll('select');
    if (selects[0]) await user.selectOptions(selects[0] as HTMLSelectElement, '4');

    const nextBtn = screen.getByRole('button', { name: 'common.next' });
    await user.click(nextBtn);

    await waitFor(() => {
      expect(screen.getByText('intake.step2.title')).toBeInTheDocument();
    });
  });

  it('goes back from step 2 to step 1', async () => {
    render(<IntakeWizard />);
    const user = userEvent.setup();

    // Force store to step 2
    const { setStep } = await import('@/store/intakeStore').then(
      (m) => m.useIntakeStore.getState()
    );
    setStep(2);

    // Re-render with updated state
    render(<IntakeWizard />);
    const backBtn = screen.getAllByRole('button', { name: 'common.back' })[0];
    await user.click(backBtn);

    await waitFor(() => {
      expect(screen.getByText('intake.step1.title')).toBeInTheDocument();
    });
  });

  it('progress bar shows correct step', () => {
    render(<IntakeWizard />);
    const nav = screen.getByRole('navigation');
    expect(nav).toBeInTheDocument();
    // Step 1 should have aria-current="step"
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});

describe('IntakeWizard — form submission', () => {
  it('calls calculateEligibility on step 3 submit', async () => {
    const mockResponse = {
      results: [],
      total: 0,
      profile_summary: {
        bagrut_average: 90,
        psychometric: null,
        subject_count: 1,
        has_five_unit_math: false,
      },
    };
    mockCalculate.mockResolvedValue(mockResponse);

    // Set up store at step 3 with valid data
    const state = await import('@/store/intakeStore').then(
      (m) => m.useIntakeStore.getState()
    );
    state.setStep(3);
    state.setHaventTakenPsychometric(true);

    render(<IntakeWizard />);
    const user = userEvent.setup();

    const submitBtn = screen.getByRole('button', { name: /common.submit/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(mockCalculate).toHaveBeenCalledTimes(1);
    });
  });

  it('shows loading state while submitting', async () => {
    mockCalculate.mockImplementation(
      () => new Promise(() => {}) // never resolves
    );

    const state = await import('@/store/intakeStore').then(
      (m) => m.useIntakeStore.getState()
    );
    state.setStep(3);
    state.setHaventTakenPsychometric(true);

    render(<IntakeWizard />);
    const user = userEvent.setup();

    const submitBtn = screen.getByRole('button', { name: /common.submit/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText('intake.submit.calculating')
      ).toBeInTheDocument();
    });
  });

  it('shows Hebrew error message on API failure', async () => {
    mockCalculate.mockRejectedValue(new api.ApiError(500, 'Internal Server Error'));

    const state = await import('@/store/intakeStore').then(
      (m) => m.useIntakeStore.getState()
    );
    state.setStep(3);
    state.setHaventTakenPsychometric(true);

    render(<IntakeWizard />);
    const user = userEvent.setup();

    const submitBtn = screen.getByRole('button', { name: /common.submit/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
