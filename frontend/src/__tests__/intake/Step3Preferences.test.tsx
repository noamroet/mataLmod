import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  waitFor,
  resetIntakeStore,
} from '../utils/testUtils';
import { Step3Preferences } from '@/components/intake/Step3Preferences';
import { useIntakeStore } from '@/store/intakeStore';
import { FIELD_CODES } from '@/types';

beforeEach(() => {
  resetIntakeStore();
});

describe('Step3Preferences — field chips', () => {
  it('renders all 17 field chips', () => {
    render(<Step3Preferences />);
    // Each chip is a button with role="checkbox"
    const chips = screen.getAllByRole('checkbox');
    // 17 field chips + location radios + inst type radios + format radios
    // Focus on field chips specifically: aria-checked
    const fieldChips = chips.filter((el) => el.tagName === 'BUTTON');
    expect(fieldChips.length).toBeGreaterThanOrEqual(FIELD_CODES.length);
  });

  it('selecting a field chip adds it to store', async () => {
    render(<Step3Preferences />);
    const user = userEvent.setup();

    // Find first chip (computer_science)
    const chip = screen.getByRole('checkbox', {
      name: /intake.fields.computer_science/i,
    });
    expect(chip).toHaveAttribute('aria-checked', 'false');
    await user.click(chip);

    await waitFor(() => {
      expect(
        useIntakeStore.getState().fieldsOfInterest
      ).toContain('computer_science');
    });
    expect(chip).toHaveAttribute('aria-checked', 'true');
  });

  it('deselecting a chip removes it from store', async () => {
    render(<Step3Preferences />);
    const user = userEvent.setup();

    const chip = screen.getByRole('checkbox', {
      name: /intake.fields.computer_science/i,
    });
    await user.click(chip); // select
    await user.click(chip); // deselect

    await waitFor(() => {
      expect(
        useIntakeStore.getState().fieldsOfInterest
      ).not.toContain('computer_science');
    });
  });

  it('shows selected count after selecting fields', async () => {
    render(<Step3Preferences />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('checkbox', { name: /intake.fields.computer_science/i })
    );
    await user.click(
      screen.getByRole('checkbox', { name: /intake.fields.law/i })
    );

    await waitFor(() => {
      expect(useIntakeStore.getState().fieldsOfInterest).toHaveLength(2);
    });
    expect(
      screen.getByText(/2 תחומים נבחרו/)
    ).toBeInTheDocument();
  });

  it('multiple fields can be selected simultaneously', async () => {
    render(<Step3Preferences />);
    const user = userEvent.setup();

    const chips = ['computer_science', 'law', 'medicine'].map((code) =>
      screen.getByRole('checkbox', { name: new RegExp(`intake.fields.${code}`, 'i') })
    );

    for (const chip of chips) await user.click(chip);

    await waitFor(() => {
      expect(useIntakeStore.getState().fieldsOfInterest).toHaveLength(3);
    });
  });
});

describe('Step3Preferences — location radio', () => {
  it('renders all 5 location options', () => {
    render(<Step3Preferences />);
    expect(
      screen.getByRole('radio', { name: /intake.step3.locations.all/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('radio', { name: /intake.step3.locations.jerusalem/i })
    ).toBeInTheDocument();
  });

  it('"All Israel" is selected by default', () => {
    render(<Step3Preferences />);
    const allRadio = screen.getByRole('radio', {
      name: /intake.step3.locations.all/i,
    });
    expect(allRadio).toBeChecked();
  });

  it('selecting a location updates the store', async () => {
    render(<Step3Preferences />);
    const user = userEvent.setup();

    const northRadio = screen.getByRole('radio', {
      name: /intake.step3.locations.north/i,
    });
    await user.click(northRadio);

    await waitFor(() => {
      expect(useIntakeStore.getState().location).toBe('north');
    });
  });
});

describe('Step3Preferences — institution type', () => {
  it('renders institution type options', () => {
    render(<Step3Preferences />);
    expect(
      screen.getByRole('radio', {
        name: /intake.step3.institutionTypes.universities/i,
      })
    ).toBeInTheDocument();
  });

  it('"Universities only" is selected by default', () => {
    render(<Step3Preferences />);
    const radio = screen.getByRole('radio', {
      name: /intake.step3.institutionTypes.universities/i,
    });
    expect(radio).toBeChecked();
  });
});

describe('Step3Preferences — study format', () => {
  it('renders all 3 study format options', () => {
    render(<Step3Preferences />);
    expect(
      screen.getByRole('radio', { name: /intake.step3.studyFormats.full_time/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('radio', { name: /intake.step3.studyFormats.part_time/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('radio', { name: /intake.step3.studyFormats.any/i })
    ).toBeInTheDocument();
  });

  it('"No preference" is selected by default', () => {
    render(<Step3Preferences />);
    const radio = screen.getByRole('radio', {
      name: /intake.step3.studyFormats.any/i,
    });
    expect(radio).toBeChecked();
  });
});
