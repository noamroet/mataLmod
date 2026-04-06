'use client';

import {
  useState,
  useRef,
  useId,
  type ReactNode,
  type KeyboardEvent,
} from 'react';

interface TooltipProps {
  label: string;          // visible trigger text / aria-label
  content: ReactNode;     // tooltip body
  children?: ReactNode;   // custom trigger; defaults to an ⓘ button
}

export function Tooltip({ label, content, children }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);

  const toggle = () => setOpen((v) => !v);
  const close = () => setOpen(false);

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      close();
      triggerRef.current?.focus();
    }
  };

  return (
    <span className="relative inline-flex">
      {children ?? (
        <button
          ref={triggerRef}
          type="button"
          aria-label={label}
          aria-expanded={open}
          aria-controls={id}
          onClick={toggle}
          onBlur={(e) => {
            // Close when focus leaves the entire tooltip widget
            if (!e.currentTarget.parentElement?.contains(e.relatedTarget as Node)) {
              close();
            }
          }}
          className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-200 text-xs font-bold text-gray-600 hover:bg-gray-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500"
        >
          ?
        </button>
      )}

      {open && (
        <div
          id={id}
          role="tooltip"
          onKeyDown={onKeyDown}
          className="absolute bottom-full start-0 z-20 mb-2 w-72 animate-fade-in rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700 shadow-lg"
        >
          {content}
          <button
            type="button"
            aria-label="סגור"
            onClick={close}
            className="mt-2 block text-xs text-primary-600 underline hover:text-primary-800"
          >
            סגור
          </button>
        </div>
      )}
    </span>
  );
}
