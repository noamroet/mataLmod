'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { useTranslations } from 'next-intl';
import { useAdvisorStore }  from '@/store/advisorStore';
import { useIntakeStore }   from '@/store/intakeStore';
import {
  WIZARD_FLOWS,
  buildPathContext,
  type CtaSection,
  type WizardChoice,
} from '@/lib/advisorFlows';
import type { AdvisorChatRequest } from '@/types';

// ── Types ─────────────────────────────────────────────────────────────────────

interface HistoryEntry {
  nodeId:          string;
  choiceLabel:     string;  // label the user clicked to reach this node
  advisorResponse: string;  // full streamed response for this step
}

// ── SSE streaming helper ──────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function streamAdvisorMessage(
  request: AdvisorChatRequest,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/advisor/chat`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(request),
  });

  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text  = decoder.decode(value, { stream: true });
    for (const line of text.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6).trim();
      if (data === '[DONE]' || data === '[TOOL_USE]' || data === '[TOOL_DONE]') continue;
      if (data) onChunk(data);
    }
  }
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ step }: { step: number }) {
  const t = useTranslations('wizard');
  return (
    <div className="px-4 pt-1" aria-label={t('stepOf', { current: step, total: 4 })}>
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              s <= step ? 'bg-primary-500' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
      <p className="mt-1 text-right text-[11px] text-gray-400">
        {t('stepOf', { current: step, total: 4 })}
      </p>
    </div>
  );
}

// ── Advisor bubble ────────────────────────────────────────────────────────────

function AdvisorBubble({
  text,
  isStreaming,
}: {
  text:        string;
  isStreaming: boolean;
}) {
  const t = useTranslations('wizard');
  return (
    <div className="flex justify-end">
      <div className="max-w-[88%] rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3 text-sm leading-relaxed text-gray-800">
        {isStreaming && !text ? (
          <span className="italic text-gray-400">{t('thinking')}</span>
        ) : (
          text
        )}
        {isStreaming && text && (
          <span className="ms-0.5 inline-block h-4 w-0.5 animate-pulse bg-gray-400" />
        )}
      </div>
    </div>
  );
}

// ── User choice bubble ────────────────────────────────────────────────────────

function UserBubble({ label }: { label: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[88%] rounded-2xl rounded-tr-sm bg-primary-600 px-4 py-2.5 text-sm font-medium text-white">
        {label}
      </div>
    </div>
  );
}

// ── Choice buttons ────────────────────────────────────────────────────────────

function ChoiceButtons({
  choices,
  disabled,
  onSelect,
}: {
  choices:  WizardChoice[];
  disabled: boolean;
  onSelect: (choice: WizardChoice) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {choices.map((c) => (
        <button
          key={c.nextId}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(c)}
          className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-right text-sm font-medium text-gray-700 transition-colors hover:border-primary-400 hover:bg-primary-50 disabled:opacity-40"
        >
          {c.label}
        </button>
      ))}
    </div>
  );
}

// ── CTA button ────────────────────────────────────────────────────────────────

function CtaButton({
  section,
  onNavigate,
}: {
  section:    CtaSection;
  onNavigate: (section: CtaSection) => void;
}) {
  const t = useTranslations('wizard.cta');
  return (
    <button
      type="button"
      onClick={() => onNavigate(section)}
      className="w-full rounded-xl bg-primary-600 px-4 py-3 text-center text-sm font-semibold text-white hover:bg-primary-700"
    >
      {t(section)} →
    </button>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

interface WizardPanelProps {
  /** Called when the user clicks a CTA to navigate to a section */
  onNavigate?: (section: CtaSection) => void;
}

export function WizardPanel({ onNavigate }: WizardPanelProps) {
  const t = useTranslations('wizard');

  const { isOpen, currentProgramId, close } = useAdvisorStore();
  const results  = useIntakeStore((s) => s.eligibilityResults);
  const bagrutGrades  = useIntakeStore((s) => s.bagrutGrades);
  const psychoScore   = useIntakeStore((s) => s.psychometricScore);

  // Find the current program info for context
  const currentResult = results?.results.find(
    (r) => r.program.id === currentProgramId
  );
  const programName   = currentResult?.program.name_he ?? 'התוכנית';
  const institutionName = currentResult?.program.institution.name_he ?? '';

  // ── Wizard state ──────────────────────────────────────────────────────────

  const [currentNodeId, setCurrentNodeId] = useState<string>('root');
  const [history,       setHistory]       = useState<HistoryEntry[]>([]);
  const [liveResponse,  setLiveResponse]  = useState<string>('');
  const [isStreaming,   setIsStreaming]    = useState<boolean>(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Reset wizard when panel opens
  useEffect(() => {
    if (isOpen) {
      setCurrentNodeId('root');
      setHistory([]);
      setLiveResponse('');
      setIsStreaming(false);
    }
  }, [isOpen]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, liveResponse, currentNodeId]);

  // Lock body scroll on mobile
  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  // ── Navigation ────────────────────────────────────────────────────────────

  const handleChoiceSelect = useCallback(
    async (choice: WizardChoice) => {
      if (isStreaming) return;

      const nextNode = WIZARD_FLOWS[choice.nextId];
      if (!nextNode) return;

      const pathLabels = [
        ...history.map((h) => h.choiceLabel),
        choice.label,
      ];
      const isFinal = nextNode.isFinal ?? false;

      // For root → branch: call API to generate step-2 advisor response
      if (nextNode.step === 1) return; // shouldn't happen

      // Build the context message for the API
      const message = buildPathContext(
        programName,
        institutionName,
        pathLabels,
        isFinal,
        t('finalPromptSuffix'),
        t('stepPromptSuffix'),
      );

      const request: AdvisorChatRequest = {
        message,
        user_profile: {
          bagrut_grades: bagrutGrades
            .filter((g) => g.subject && g.units && g.grade !== '')
            .map((g) => ({
              subject_code: g.subject,
              units:        g.units as 3 | 4 | 5,
              grade:        g.grade as number,
            })),
          psychometric: psychoScore !== '' ? (psychoScore as number) : null,
        },
        current_program_id: currentProgramId ?? null,
        conversation_history: [],
      };

      // Optimistically navigate & start streaming
      setCurrentNodeId(choice.nextId);
      setLiveResponse('');
      setIsStreaming(true);

      let fullResponse = '';
      try {
        await streamAdvisorMessage(request, (chunk) => {
          fullResponse += chunk;
          setLiveResponse((prev) => prev + chunk);
        });
      } catch {
        fullResponse = '(שגיאה בטעינת התשובה — נסה שוב)';
        setLiveResponse(fullResponse);
      } finally {
        setIsStreaming(false);
      }

      // Commit to history
      setHistory((prev) => [
        ...prev,
        {
          nodeId:          choice.nextId,
          choiceLabel:     choice.label,
          advisorResponse: fullResponse,
        },
      ]);
      setLiveResponse('');
    },
    [
      isStreaming, history, programName, institutionName,
      bagrutGrades, psychoScore, currentProgramId, t,
    ]
  );

  const handleBack = () => {
    if (history.length === 0) return;
    const prev = history[history.length - 2];
    setHistory((h) => h.slice(0, -1));
    setCurrentNodeId(prev?.nodeId ?? 'root');
    setLiveResponse('');
  };

  const handleNavigate = (section: CtaSection) => {
    close();
    onNavigate?.(section);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  if (!isOpen) return null;

  const currentNode = WIZARD_FLOWS[currentNodeId];
  if (!currentNode) return null;

  const currentStep = currentNode.step;

  return (
    <>
      {/* Backdrop (mobile) */}
      <div
        className="fixed inset-0 z-40 bg-black/40 lg:hidden"
        aria-hidden="true"
        onClick={close}
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('panelTitle')}
        className={[
          'fixed z-50 flex flex-col bg-white shadow-2xl',
          'inset-x-0 bottom-0 h-[90vh] rounded-t-2xl',
          'lg:inset-y-0 lg:end-0 lg:top-0 lg:h-full lg:w-[420px] lg:rounded-none',
        ].join(' ')}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-gray-100 px-4 py-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900">{t('panelTitle')}</h2>
            <button
              type="button"
              onClick={close}
              aria-label={t('close')}
              className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
          <ProgressBar step={currentStep} />
        </div>

        {/* Conversation */}
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {/* Step 1 — static root message */}
          <AdvisorBubble text={t('root.message')} isStreaming={false} />

          {/* Replayed history */}
          {history.map((entry, i) => (
            <div key={i} className="space-y-3">
              <UserBubble label={entry.choiceLabel} />
              {entry.advisorResponse && (
                <AdvisorBubble text={entry.advisorResponse} isStreaming={false} />
              )}
            </div>
          ))}

          {/* Live streaming response */}
          {(isStreaming || liveResponse) && (
            <AdvisorBubble text={liveResponse} isStreaming={isStreaming} />
          )}

          <div ref={scrollRef} />
        </div>

        {/* Action area */}
        <div className="shrink-0 space-y-3 border-t border-gray-100 px-4 py-4">
          {!isStreaming && currentNode.isFinal ? (
            /* Final step: CTA */
            <CtaButton
              section={currentNode.ctaSection ?? 'details'}
              onNavigate={handleNavigate}
            />
          ) : !isStreaming ? (
            /* Choice buttons */
            <>
              <ChoiceButtons
                choices={currentNode.choices}
                disabled={isStreaming}
                onSelect={handleChoiceSelect}
              />
              {currentStep > 1 && (
                <button
                  type="button"
                  onClick={handleBack}
                  className="w-full rounded-xl border border-gray-200 px-4 py-2 text-sm text-gray-500 hover:bg-gray-50"
                >
                  ← {t('back')}
                </button>
              )}
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}
