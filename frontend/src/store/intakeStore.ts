'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  BagrutGradeEntry,
  EligibilityResponse,
  FieldCode,
  LocationFilter,
  InstitutionTypeFilter,
  StudyFormatFilter,
} from '@/types';

// ── Weighted average (mirrors backend sekem.weighted_bagrut_average) ──────────

export function weightedBagrutAverage(grades: BagrutGradeEntry[]): number {
  const valid = grades.filter(
    (g) => g.subject !== '' && g.units !== null && g.grade !== ''
  );
  if (valid.length === 0) return 0;
  let totalWeight = 0;
  let totalWeightedGrade = 0;
  for (const g of valid) {
    const units = g.units as 3 | 4 | 5;
    const multiplier = units === 5 ? 1.25 : 1.0;
    const ew = units * multiplier;
    totalWeight += ew;
    totalWeightedGrade += (g.grade as number) * ew;
  }
  return totalWeight > 0 ? totalWeightedGrade / totalWeight : 0;
}

function newGradeEntry(): BagrutGradeEntry {
  return {
    id:      crypto.randomUUID(),
    subject: '',
    units:   null,
    grade:   '',
  };
}

// ── State shape ───────────────────────────────────────────────────────────────

interface IntakeState {
  // ── Step 1
  bagrutGrades: BagrutGradeEntry[];
  useEstimatedAverage: boolean;
  estimatedAverage: number | '';

  // ── Step 2
  psychometricScore: number | '';
  haventTakenPsychometric: boolean;

  // ── Step 3
  fieldsOfInterest: FieldCode[];
  location: LocationFilter;
  institutionType: InstitutionTypeFilter;
  studyFormat: StudyFormatFilter;

  // ── Wizard navigation
  currentStep: 1 | 2 | 3;

  // ── Results (set after successful submit)
  eligibilityResults: EligibilityResponse | null;

  // ── Actions
  setStep: (step: 1 | 2 | 3) => void;

  addGrade: () => void;
  updateGrade: <K extends keyof BagrutGradeEntry>(
    id: string,
    field: K,
    value: BagrutGradeEntry[K]
  ) => void;
  removeGrade: (id: string) => void;

  setUseEstimatedAverage: (v: boolean) => void;
  setEstimatedAverage: (v: number | '') => void;

  setPsychometricScore: (v: number | '') => void;
  setHaventTakenPsychometric: (v: boolean) => void;

  toggleField: (field: FieldCode) => void;
  setLocation: (v: LocationFilter) => void;
  setInstitutionType: (v: InstitutionTypeFilter) => void;
  setStudyFormat: (v: StudyFormatFilter) => void;

  setEligibilityResults: (results: EligibilityResponse) => void;

  reset: () => void;
}

const initialState: Omit<
  IntakeState,
  | 'setStep'
  | 'addGrade'
  | 'updateGrade'
  | 'removeGrade'
  | 'setUseEstimatedAverage'
  | 'setEstimatedAverage'
  | 'setPsychometricScore'
  | 'setHaventTakenPsychometric'
  | 'toggleField'
  | 'setLocation'
  | 'setInstitutionType'
  | 'setStudyFormat'
  | 'setEligibilityResults'
  | 'reset'
> = {
  bagrutGrades:           [newGradeEntry()],
  useEstimatedAverage:    false,
  estimatedAverage:       '',
  psychometricScore:      '',
  haventTakenPsychometric: false,
  fieldsOfInterest:       [],
  location:               'all',
  institutionType:        'universities',
  studyFormat:            'any',
  currentStep:            1,
  eligibilityResults:     null,
};

// ── Store ─────────────────────────────────────────────────────────────────────

export const useIntakeStore = create<IntakeState>()(
  persist(
    (set) => ({
      ...initialState,

      setStep: (step) => set({ currentStep: step }),

      addGrade: () =>
        set((s) => ({ bagrutGrades: [...s.bagrutGrades, newGradeEntry()] })),

      updateGrade: (id, field, value) =>
        set((s) => ({
          bagrutGrades: s.bagrutGrades.map((g) =>
            g.id === id ? { ...g, [field]: value } : g
          ),
        })),

      removeGrade: (id) =>
        set((s) => ({
          bagrutGrades: s.bagrutGrades.filter((g) => g.id !== id),
        })),

      setUseEstimatedAverage: (v) =>
        set({ useEstimatedAverage: v, bagrutGrades: v ? [] : [newGradeEntry()] }),

      setEstimatedAverage: (v) => set({ estimatedAverage: v }),

      setPsychometricScore: (v) => set({ psychometricScore: v }),

      setHaventTakenPsychometric: (v) =>
        set({ haventTakenPsychometric: v, psychometricScore: v ? '' : '' }),

      toggleField: (field) =>
        set((s) => ({
          fieldsOfInterest: s.fieldsOfInterest.includes(field)
            ? s.fieldsOfInterest.filter((f) => f !== field)
            : [...s.fieldsOfInterest, field],
        })),

      setLocation: (v) => set({ location: v }),
      setInstitutionType: (v) => set({ institutionType: v }),
      setStudyFormat: (v) => set({ studyFormat: v }),

      setEligibilityResults: (results) => set({ eligibilityResults: results }),

      reset: () => set({ ...initialState, bagrutGrades: [newGradeEntry()] }),
    }),
    {
      name:    'mataLmod-intake',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? sessionStorage : localStorage
      ),
      // Don't persist results — they're ephemeral (computed on submit).
      partialize: (state) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { eligibilityResults, ...rest } = state;
        return rest;
      },
      // Never let stored data overwrite in-memory eligibilityResults.
      // Old sessionStorage entries may have eligibilityResults: null which
      // would race-overwrite the freshly-set results after navigation.
      merge: (persistedState, currentState) => ({
        ...(currentState as IntakeState),
        ...(persistedState as Partial<IntakeState>),
        eligibilityResults: (currentState as IntakeState).eligibilityResults,
      }),
    }
  )
);
