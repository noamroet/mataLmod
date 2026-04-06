import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  waitFor,
  within,
  resetIntakeStore,
} from '../utils/testUtils';
import { ResultsClient } from '@/components/results/ResultsClient';
import { useIntakeStore } from '@/store/intakeStore';
import { useComparisonStore } from '@/store/comparisonStore';
import {
  makeResultItem,
  makeEligibilityResponse,
  makeProgram,
} from './fixtures';

beforeEach(() => {
  resetIntakeStore();
  useComparisonStore.getState().clearComparison();
});

function seedResults(items = [makeResultItem()]) {
  useIntakeStore.getState().setEligibilityResults(makeEligibilityResponse(items));
}

// ── Redirect when no results ──────────────────────────────────────────────────

describe('ResultsClient — redirect', () => {
  it('shows redirecting message when store has no results', () => {
    render(<ResultsClient />);
    expect(screen.getByText('results.redirecting')).toBeInTheDocument();
  });
});

// ── Renders results ───────────────────────────────────────────────────────────

describe('ResultsClient — rendering', () => {
  it('renders results title', () => {
    seedResults();
    render(<ResultsClient />);
    expect(screen.getByText('results.title')).toBeInTheDocument();
  });

  it('renders a card for each result', () => {
    seedResults([
      makeResultItem({ program: makeProgram({ name_he: 'מדעי המחשב' }) }),
      makeResultItem({ rank: 2, program: makeProgram({ name_he: 'הנדסת חשמל', field: 'electrical_engineering' }) }),
    ]);
    render(<ResultsClient />);
    expect(screen.getByText('מדעי המחשב')).toBeInTheDocument();
    expect(screen.getByText('הנדסת חשמל')).toBeInTheDocument();
  });

  it('shows profile summary bar with correct values', () => {
    seedResults();
    render(<ResultsClient />);
    expect(screen.getByText(/90/)).toBeInTheDocument(); // bagrut avg
    expect(screen.getByText(/680/)).toBeInTheDocument(); // psychometric
  });

  it('shows subtitle with total count', () => {
    seedResults([makeResultItem(), makeResultItem({ rank: 2 })]);
    render(<ResultsClient />);
    expect(screen.getByText(/results.subtitle/)).toBeInTheDocument();
  });
});

// ── Sorting ───────────────────────────────────────────────────────────────────

describe('ResultsClient — sorting', () => {
  it('renders sort dropdown', () => {
    seedResults();
    render(<ResultsClient />);
    expect(screen.getByRole('combobox', { hidden: true }) ?? screen.getByRole('listbox', { hidden: true })).toBeDefined();
    // The sort select element
    expect(document.querySelector('select')).toBeInTheDocument();
  });

  it('sorts by margin by default (eligible first)', () => {
    const eligible = makeResultItem({ rank: 2, sekem: 760, threshold: 730, margin: 30, eligible: true, program: makeProgram({ name_he: 'תוכנית א' }) });
    const ineligible = makeResultItem({ rank: 1, sekem: 600, threshold: 730, margin: -130, eligible: false, borderline: false, program: makeProgram({ name_he: 'תוכנית ב' }) });
    seedResults([ineligible, eligible]);
    render(<ResultsClient />);

    const cards = screen.getAllByRole('article');
    // First card should be the eligible one
    expect(within(cards[0]).getByText('תוכנית א')).toBeInTheDocument();
  });

  it('changes sort order when dropdown changes', async () => {
    seedResults([
      makeResultItem({ program: makeProgram({ name_he: 'ת' }), sekem: 760, margin: 30 }),
      makeResultItem({ rank: 2, program: makeProgram({ name_he: 'א' }), sekem: 740, margin: 10 }),
    ]);
    render(<ResultsClient />);
    const user = userEvent.setup();

    const select = document.querySelector('select') as HTMLSelectElement;
    await user.selectOptions(select, 'alpha');

    // Re-render should now show alphabetical order — 'א' before 'ת'
    const cards = screen.getAllByRole('article');
    expect(within(cards[0]).getByText('א')).toBeInTheDocument();
  });
});

// ── Filtering ─────────────────────────────────────────────────────────────────

describe('ResultsClient — filtering', () => {
  it('renders filter button on mobile', () => {
    seedResults();
    render(<ResultsClient />);
    expect(
      screen.getByRole('button', { name: /results.filters.openButton/i })
    ).toBeInTheDocument();
  });

  it('opens mobile filter panel when button is clicked', async () => {
    seedResults();
    render(<ResultsClient />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('button', { name: /results.filters.openButton/i })
    );

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  it('shows empty state when all results are filtered out', async () => {
    seedResults([
      makeResultItem({ eligible: true, borderline: false }),
    ]);
    render(<ResultsClient />);
    const user = userEvent.setup();

    // Open filter panel (mobile button)
    await user.click(
      screen.getByRole('button', { name: /results.filters.openButton/i })
    );

    // Click "below" filter — this will filter out the eligible result
    const belowCheckbox = screen.getByRole('checkbox', { name: /results.filters.below/i });
    await user.click(belowCheckbox);

    await waitFor(() => {
      expect(screen.getByText('results.noResults')).toBeInTheDocument();
    });
  });

  it('shows "clear filters" button in empty state', async () => {
    seedResults([makeResultItem({ eligible: true })]);
    render(<ResultsClient />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole('button', { name: /results.filters.openButton/i })
    );
    await user.click(screen.getByRole('checkbox', { name: /results.filters.below/i }));

    await waitFor(() => {
      expect(screen.getByText('results.noResultsClear')).toBeInTheDocument();
    });
  });

  it('clearing filters restores all results', async () => {
    seedResults([makeResultItem({ eligible: true })]);
    render(<ResultsClient />);
    const user = userEvent.setup();

    // Filter to below-threshold (hides our eligible result)
    await user.click(
      screen.getByRole('button', { name: /results.filters.openButton/i })
    );
    await user.click(screen.getByRole('checkbox', { name: /results.filters.below/i }));

    await waitFor(() => expect(screen.getByText('results.noResults')).toBeInTheDocument());

    // Clear filters
    await user.click(screen.getByText('results.noResultsClear'));

    await waitFor(() => {
      expect(screen.queryByText('results.noResults')).not.toBeInTheDocument();
    });
  });
});

// ── Comparison bar ────────────────────────────────────────────────────────────

describe('ResultsClient — comparison bar', () => {
  it('comparison bar is not visible when nothing is selected', () => {
    seedResults();
    render(<ResultsClient />);
    expect(
      screen.queryByRole('region', { name: /results.comparison.title/i })
    ).not.toBeInTheDocument();
  });

  it('comparison bar appears when a program is selected', async () => {
    const item = makeResultItem();
    seedResults([item]);
    render(<ResultsClient />);
    const user = userEvent.setup();

    // Click compare button on the card
    await user.click(screen.getByRole('button', { name: /results.card.compare/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('region', { name: /results.comparison.title/i })
      ).toBeInTheDocument();
    });
  });
});
