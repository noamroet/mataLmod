'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const MAX_COMPARISON = 3;

interface ComparisonState {
  selectedIds: string[];
  addProgram: (id: string) => void;
  removeProgram: (id: string) => void;
  toggleProgram: (id: string) => void;
  clearComparison: () => void;
  isSelected: (id: string) => boolean;
  canAdd: () => boolean;
}

export const useComparisonStore = create<ComparisonState>()(
  persist(
    (set, get) => ({
      selectedIds: [],

      addProgram: (id) =>
        set((s) =>
          s.selectedIds.length < MAX_COMPARISON && !s.selectedIds.includes(id)
            ? { selectedIds: [...s.selectedIds, id] }
            : s
        ),

      removeProgram: (id) =>
        set((s) => ({ selectedIds: s.selectedIds.filter((x) => x !== id) })),

      toggleProgram: (id) => {
        const { selectedIds } = get();
        if (selectedIds.includes(id)) {
          set({ selectedIds: selectedIds.filter((x) => x !== id) });
        } else if (selectedIds.length < MAX_COMPARISON) {
          set({ selectedIds: [...selectedIds, id] });
        }
      },

      clearComparison: () => set({ selectedIds: [] }),

      isSelected: (id) => get().selectedIds.includes(id),

      canAdd: () => get().selectedIds.length < MAX_COMPARISON,
    }),
    {
      name: 'mataLmod-comparison',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? sessionStorage : localStorage
      ),
    }
  )
);

export const MAX_COMPARISON_PROGRAMS = MAX_COMPARISON;
