import userEvent from '@testing-library/user-event';
import {
  render,
  screen,
  within,
  resetIntakeStore,
} from '../utils/testUtils';
import { ProgramCard } from '@/components/results/ProgramCard';
import { useComparisonStore } from '@/store/comparisonStore';
import { makeResultItem } from './fixtures';

beforeEach(() => {
  resetIntakeStore();
  useComparisonStore.getState().clearComparison();
});

// ── Rendering ─────────────────────────────────────────────────────────────────

describe('ProgramCard — rendering', () => {
  it('shows program name in Hebrew', () => {
    render(<ProgramCard item={makeResultItem()} />);
    expect(screen.getByText('מדעי המחשב')).toBeInTheDocument();
  });

  it('shows institution name', () => {
    render(<ProgramCard item={makeResultItem()} />);
    expect(screen.getByText('אוניברסיטת תל אביב')).toBeInTheDocument();
  });

  it('shows eligible badge for eligible program', () => {
    render(
      <ProgramCard item={makeResultItem({ eligible: true, borderline: false })} />
    );
    expect(screen.getByText('program.eligibility.eligible')).toBeInTheDocument();
  });

  it('shows borderline badge for borderline program', () => {
    render(
      <ProgramCard
        item={makeResultItem({
          eligible:   false,
          borderline: true,
          sekem:      710,
          threshold:  730,
          margin:     -20,
        })}
      />
    );
    expect(screen.getByText('program.eligibility.borderline')).toBeInTheDocument();
  });

  it('shows below-threshold badge', () => {
    render(
      <ProgramCard
        item={makeResultItem({
          eligible:   false,
          borderline: false,
          sekem:      650,
          threshold:  730,
          margin:     -80,
        })}
      />
    );
    expect(screen.getByText('program.eligibility.belowThreshold')).toBeInTheDocument();
  });

  it('shows sekem and threshold values', () => {
    render(<ProgramCard item={makeResultItem({ sekem: 740, threshold: 730 })} />);
    expect(screen.getByText(/740/)).toBeInTheDocument();
    expect(screen.getByText(/730/)).toBeInTheDocument();
  });

  it('shows degree type and duration', () => {
    render(<ProgramCard item={makeResultItem()} />);
    expect(screen.getByText('BSc')).toBeInTheDocument();
    expect(screen.getByText(/results.card.duration/)).toBeInTheDocument();
  });

  it('shows location', () => {
    render(<ProgramCard item={makeResultItem()} />);
    expect(screen.getByText('תל אביב')).toBeInTheDocument();
  });

  it('links to program detail page', () => {
    const item = makeResultItem();
    render(<ProgramCard item={item} />);
    const links = screen.getAllByRole('link');
    const detailLink = links.find((l) =>
      l.getAttribute('href')?.includes(item.program.id)
    );
    expect(detailLink).toBeInTheDocument();
  });
});

// ── Compare button ────────────────────────────────────────────────────────────

describe('ProgramCard — compare button', () => {
  it('has aria-pressed=false initially', () => {
    render(<ProgramCard item={makeResultItem()} />);
    const btn = screen.getByRole('button', { name: /results.card.compare/i });
    expect(btn).toHaveAttribute('aria-pressed', 'false');
  });

  it('toggles program into comparison store on click', async () => {
    const item = makeResultItem();
    render(<ProgramCard item={item} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /results.card.compare/i }));

    expect(useComparisonStore.getState().isSelected(item.program.id)).toBe(true);
  });

  it('shows compareAdded text when selected', async () => {
    const item = makeResultItem();
    render(<ProgramCard item={item} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('results.card.compareAdded')).toBeInTheDocument();
  });

  it('removes from comparison when clicked again', async () => {
    const item = makeResultItem();
    render(<ProgramCard item={item} />);
    const user = userEvent.setup();

    const btn = screen.getByRole('button');
    await user.click(btn); // add
    await user.click(btn); // remove

    expect(useComparisonStore.getState().isSelected(item.program.id)).toBe(false);
  });

  it('disables button when comparison is full (3 items) and this one is not selected', async () => {
    // Pre-fill 3 different programs into comparison
    const store = useComparisonStore.getState();
    store.addProgram('id-a');
    store.addProgram('id-b');
    store.addProgram('id-c');

    const item = makeResultItem(); // different id
    render(<ProgramCard item={item} />);

    const btn = screen.getByRole('button', { name: /results.card.compare/i });
    expect(btn).toBeDisabled();
  });
});

// ── Margin display ────────────────────────────────────────────────────────────

describe('ProgramCard — margin display', () => {
  it('shows positive margin with + prefix', () => {
    render(<ProgramCard item={makeResultItem({ sekem: 760, threshold: 730, margin: 30 })} />);
    expect(screen.getByText(/results.card.positiveMargin/)).toBeInTheDocument();
  });

  it('shows negative margin for ineligible program', () => {
    render(
      <ProgramCard
        item={makeResultItem({
          eligible:   false,
          borderline: false,
          sekem:      650,
          threshold:  730,
          margin:     -80,
        })}
      />
    );
    expect(screen.getByText(/results.card.negativeMargin/)).toBeInTheDocument();
  });
});
