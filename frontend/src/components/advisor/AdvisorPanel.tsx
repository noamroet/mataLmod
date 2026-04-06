'use client';

import {
  useEffect,
  useRef,
  useState,
  FormEvent,
  KeyboardEvent,
} from 'react';
import { useTranslations } from 'next-intl';
import { useAdvisorStore } from '@/store/advisorStore';
import { useIntakeStore } from '@/store/intakeStore';
import type { AdvisorChatRequest } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── SSE streaming send ─────────────────────────────────────────────────────────

async function streamAdvisorMessage(
  request: AdvisorChatRequest,
  onChunk: (text: string) => void,
  onToolUse: (active: boolean) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/advisor/chat`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(request),
  });

  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`);
  }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text  = decoder.decode(value, { stream: true });
    const lines = text.split('\n');

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6).trim();

      if (data === '[DONE]') {
        onToolUse(false);
        return;
      }
      if (data === '[TOOL_USE]') {
        onToolUse(true);
        continue;
      }
      if (data === '[TOOL_DONE]') {
        onToolUse(false);
        continue;
      }
      if (data) onChunk(data);
    }
  }
}

// ── Message bubble ─────────────────────────────────────────────────────────────

function MessageBubble({
  role,
  content,
}: {
  role: 'user' | 'assistant';
  content: string;
}) {
  const isUser = role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        {content}
      </div>
    </div>
  );
}

// ── Main panel ─────────────────────────────────────────────────────────────────

export function AdvisorPanel() {
  const t = useTranslations('advisor');

  const {
    isOpen,
    messages,
    isStreaming,
    currentProgramId,
    close,
    addMessage,
    appendToLastMessage,
    setIsStreaming,
  } = useAdvisorStore();

  const bagrutGrades = useIntakeStore((s) => s.bagrutGrades);
  const psycho       = useIntakeStore((s) => s.psychometricScore);
  const results      = useIntakeStore((s) => s.eligibilityResults);

  const [input,       setInput]       = useState('');
  const [error,       setError]       = useState<string | null>(null);
  const [toolActive,  setToolActive]  = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Seed greeting when panel first opens
  useEffect(() => {
    if (!isOpen) return;
    if (messages.length > 0) return;

    const topProgram = results?.results[0]?.program.name_he ?? null;
    const greeting =
      topProgram && !currentProgramId
        ? t('greetingWithProgram', { program: topProgram })
        : currentProgramId
        ? t('greetingWithProgram', {
            program:
              results?.results.find((r) => r.program.id === currentProgramId)
                ?.program.name_he ?? t('panelTitle'),
          })
        : t('greeting');

    addMessage({ role: 'assistant', content: greeting });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Lock body scroll when panel open on mobile
  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  const handleClose = () => {
    close();
  };

  const handleSend = async (text: string) => {
    if (!text.trim() || isStreaming) return;

    setError(null);
    addMessage({ role: 'user', content: text });
    setInput('');
    setIsStreaming(true);

    // Prepare history without the just-added user message for request
    const history = messages.filter((m) => m.role !== 'user' || m.content !== text);

    const request: AdvisorChatRequest = {
      message: text,
      user_profile: {
        bagrut_grades: bagrutGrades
          .filter((g) => g.subject && g.units && g.grade !== '')
          .map((g) => ({
            subject_code: g.subject,
            units:        g.units as 3 | 4 | 5,
            grade:        g.grade as number,
          })),
        psychometric: psycho !== '' ? (psycho as number) : null,
      },
      current_program_id: currentProgramId,
      conversation_history: history,
    };

    // Add empty assistant placeholder
    addMessage({ role: 'assistant', content: '' });

    try {
      await streamAdvisorMessage(
        request,
        (chunk) => appendToLastMessage(chunk),
        (active) => setToolActive(active)
      );
    } catch {
      setError(t('errorMessage'));
      // Replace the empty assistant placeholder with the error text
      appendToLastMessage(t('errorMessage'));
    } finally {
      setIsStreaming(false);
      setToolActive(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    handleSend(input);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop (mobile) */}
      <div
        className="fixed inset-0 z-40 bg-black/40 lg:hidden"
        aria-hidden="true"
        onClick={handleClose}
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('panelTitle')}
        className={[
          'fixed z-50 flex flex-col bg-white shadow-2xl',
          // Mobile: bottom sheet
          'inset-x-0 bottom-0 h-[85vh] rounded-t-2xl',
          // Desktop: sidebar on the end side
          'lg:inset-y-0 lg:end-0 lg:top-0 lg:h-full lg:w-[400px] lg:rounded-none',
        ].join(' ')}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-gray-100 px-4 py-3">
          <h2 className="text-base font-bold text-gray-900">{t('panelTitle')}</h2>
          <button
            type="button"
            onClick={handleClose}
            aria-label={t('close')}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.map((msg, idx) => (
            <MessageBubble key={idx} role={msg.role} content={msg.content} />
          ))}

          {/* Tool-use indicator */}
          {toolActive && (
            <div className="flex justify-start">
              <span className="rounded-2xl bg-gray-100 px-4 py-2.5 text-xs italic text-gray-500">
                {t('toolUse')}
              </span>
            </div>
          )}

          {/* Streaming indicator */}
          {isStreaming && !toolActive && messages[messages.length - 1]?.content === '' && (
            <div className="flex justify-start">
              <span className="rounded-2xl bg-gray-100 px-4 py-2.5 text-xs italic text-gray-500">
                {t('thinking')}
              </span>
            </div>
          )}

          {error && (
            <p role="alert" className="text-center text-xs text-red-600">
              {error}
            </p>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Disclaimer */}
        <p className="shrink-0 px-4 pb-1 text-center text-[11px] text-gray-400">
          {t('disclaimer')}
        </p>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="shrink-0 border-t border-gray-100 px-4 py-3"
        >
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('placeholder')}
              rows={1}
              disabled={isStreaming}
              aria-label={t('placeholder')}
              className="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              aria-label={t('send')}
              className="shrink-0 rounded-xl bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-40"
            >
              {t('send')}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
