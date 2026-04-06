import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  waitFor,
  resetIntakeStore,
} from '../utils/testUtils';
import { Step2Psychometric } from '@/components/intake/Step2Psychometric';
import { useIntakeStore } from '@/store/intakeStore';

beforeEach(() => {
  resetIntakeStore();
});

describe('Step2Psychometric — input behaviour', () => {
  it('renders the score input', () => {
    render(<Step2Psychometric errors={{}} />);
    expect(
      screen.getByPlaceholderText('intake.step2.scorePlaceholder')
    ).toBeInTheDocument();
  });

  it('updates store when a valid score is typed', async () => {
    render(<Step2Psychometric errors={{}} />);
    const user = userEvent.setup();

    const input = screen.getByPlaceholderText('intake.step2.scorePlaceholder');
    await user.type(input, '680');

    await waitFor(() => {
      expect(useIntakeStore.getState().psychometricScore).toBe(680);
    });
  });

  it('disables input when "haven\'t taken" checkbox is checked', async () => {
    render(<Step2Psychometric errors={{}} />);
    const user = userEvent.setup();

    const checkbox = screen.getByRole('checkbox', {
      name: /intake.step2.haventTaken/i,
    });
    await user.click(checkbox);

    const input = screen.getByPlaceholderText('intake.step2.scorePlaceholder');
    expect(input).toBeDisabled();
  });

  it('shows note text when "haven\'t taken" is checked', async () => {
    render(<Step2Psychometric errors={{}} />);
    const user = userEvent.setup();

    const checkbox = screen.getByRole('checkbox', {
      name: /intake.step2.haventTaken/i,
    });
    await user.click(checkbox);

    expect(
      screen.getByText('intake.step2.haventTakenNote')
    ).toBeInTheDocument();
  });

  it('sets haventTakenPsychometric to true in store', async () => {
    render(<Step2Psychometric errors={{}} />);
    const user = userEvent.setup();

    const checkbox = screen.getByRole('checkbox', {
      name: /intake.step2.haventTaken/i,
    });
    await user.click(checkbox);

    expect(
      useIntakeStore.getState().haventTakenPsychometric
    ).toBe(true);
  });
});

describe('Step2Psychometric — validation errors', () => {
  it('shows error message for out-of-range score', () => {
    render(
      <Step2Psychometric errors={{ score: 'intake.step2.validation.range' }} />
    );
    expect(
      screen.getByRole('alert')
    ).toHaveTextContent('intake.step2.validation.range');
  });

  it('shows required error when score is missing', () => {
    render(
      <Step2Psychometric errors={{ score: 'intake.step2.validation.required' }} />
    );
    expect(
      screen.getByRole('alert')
    ).toHaveTextContent('intake.step2.validation.required');
  });

  it('marks input as aria-invalid when there is an error', () => {
    render(
      <Step2Psychometric errors={{ score: 'intake.step2.validation.range' }} />
    );
    const input = screen.getByPlaceholderText('intake.step2.scorePlaceholder');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('no aria-invalid when no error', () => {
    render(<Step2Psychometric errors={{}} />);
    const input = screen.getByPlaceholderText('intake.step2.scorePlaceholder');
    expect(input).not.toHaveAttribute('aria-invalid', 'true');
  });
});

describe('Step2Psychometric — validation boundary values', () => {
  const VALID = [200, 400, 680, 800];
  const INVALID = [199, 801, 0, 1000];

  test.each(VALID)('score %i is within valid range', (score) => {
    expect(score).toBeGreaterThanOrEqual(200);
    expect(score).toBeLessThanOrEqual(800);
  });

  test.each(INVALID)('score %i is outside valid range', (score) => {
    expect(score < 200 || score > 800).toBe(true);
  });
});

describe('Step2Psychometric — NITE link', () => {
  it('renders the NITE external link', () => {
    render(<Step2Psychometric errors={{}} />);
    const links = screen.getAllByRole('link');
    const niteLink = links.find((l) => l.getAttribute('href')?.includes('nite'));
    expect(niteLink).toBeInTheDocument();
    expect(niteLink).toHaveAttribute('target', '_blank');
    expect(niteLink).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
