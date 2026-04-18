'use client';

import { create } from 'zustand';

interface AdvisorMessage {
  role:    'user' | 'assistant';
  content: string;
}

// ── State ─────────────────────────────────────────────────────────────────────

interface AdvisorState {
  isOpen:           boolean;
  messages:         AdvisorMessage[];
  isStreaming:      boolean;
  currentProgramId: string | null;

  open:                (programId?: string | null) => void;
  close:               () => void;
  addMessage:          (msg: AdvisorMessage) => void;
  appendToLastMessage: (chunk: string) => void;
  setIsStreaming:      (v: boolean) => void;
  clearMessages:       () => void;
}

// ── Store (not persisted — messages are ephemeral) ────────────────────────────

export const useAdvisorStore = create<AdvisorState>()((set) => ({
  isOpen:           false,
  messages:         [],
  isStreaming:      false,
  currentProgramId: null,

  open: (programId = null) =>
    set((s) => ({
      isOpen:           true,
      currentProgramId: programId ?? s.currentProgramId,
    })),

  close: () => set({ isOpen: false }),

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  appendToLastMessage: (chunk) =>
    set((s) => {
      if (s.messages.length === 0) return s;
      const msgs = [...s.messages];
      msgs[msgs.length - 1] = {
        ...msgs[msgs.length - 1],
        content: msgs[msgs.length - 1].content + chunk,
      };
      return { messages: msgs };
    }),

  setIsStreaming: (v) => set({ isStreaming: v }),

  clearMessages: () => set({ messages: [] }),
}));
