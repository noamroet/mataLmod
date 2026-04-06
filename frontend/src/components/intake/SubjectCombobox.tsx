'use client';

import {
  useState,
  useRef,
  useId,
  useEffect,
  type KeyboardEvent,
} from 'react';
import { useTranslations } from 'next-intl';
import { SUBJECT_CODES, type SubjectCode } from '@/types';

interface SubjectComboboxProps {
  value: string;
  onChange: (code: SubjectCode | '') => void;
  usedSubjects: string[];   // already-selected codes in other rows
  id?: string;
  'aria-labelledby'?: string;
  'aria-describedby'?: string;
  hasError?: boolean;
}

export function SubjectCombobox({
  value,
  onChange,
  usedSubjects,
  id,
  'aria-labelledby': labelledBy,
  'aria-describedby': describedBy,
  hasError,
}: SubjectComboboxProps) {
  const t = useTranslations('intake.subjects');
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  // Display the label of the currently selected subject
  const selectedLabel = value ? t(value as SubjectCode) : '';

  // Build the options: filter by query, exclude already-used
  const allOptions = SUBJECT_CODES.map((code) => ({
    code,
    label: t(code),
  }));

  const filtered = allOptions.filter(
    (o) =>
      (usedSubjects.includes(o.code) ? o.code === value : true) &&
      o.label.includes(query)
  );

  const openList = () => {
    setQuery('');
    setOpen(true);
    setActiveIndex(-1);
  };

  const closeList = () => {
    setOpen(false);
    setActiveIndex(-1);
  };

  const selectOption = (code: SubjectCode) => {
    onChange(code);
    setQuery('');
    closeList();
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        e.preventDefault();
        openList();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (activeIndex >= 0 && filtered[activeIndex]) {
          selectOption(filtered[activeIndex].code as SubjectCode);
        }
        break;
      case 'Escape':
        e.preventDefault();
        closeList();
        break;
      case 'Tab':
        closeList();
        break;
    }
  };

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const item = listRef.current.children[activeIndex] as HTMLElement | undefined;
      item?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIndex]);

  const displayValue = open ? query : selectedLabel;

  return (
    <div className="relative">
      <input
        ref={inputRef}
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined
        }
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        aria-invalid={hasError ? 'true' : undefined}
        value={displayValue}
        placeholder={t('searchPlaceholder')}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!open) setOpen(true);
          setActiveIndex(-1);
        }}
        onFocus={openList}
        onBlur={(e) => {
          // Delay so click on option registers first
          setTimeout(() => {
            if (!listRef.current?.contains(document.activeElement)) {
              closeList();
            }
          }, 150);
        }}
        onKeyDown={handleKeyDown}
        className={[
          'w-full rounded-lg border px-3 py-2 text-sm transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-primary-500',
          hasError
            ? 'border-red-400 bg-red-50 focus:ring-red-400'
            : 'border-gray-300 bg-white focus:border-primary-400',
        ].join(' ')}
        autoComplete="off"
        spellCheck={false}
      />

      {open && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-label={t('searchPlaceholder')}
          className="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg animate-fade-in"
        >
          {filtered.length === 0 ? (
            <li
              role="option"
              aria-selected="false"
              className="px-3 py-2 text-sm text-gray-400"
            >
              {t('noResults')}
            </li>
          ) : (
            filtered.map((o, idx) => {
              const isActive   = idx === activeIndex;
              const isSelected = o.code === value;
              const isDisabled = usedSubjects.includes(o.code) && o.code !== value;

              return (
                <li
                  key={o.code}
                  id={`${listId}-option-${idx}`}
                  role="option"
                  aria-selected={isSelected}
                  aria-disabled={isDisabled}
                  onClick={() => !isDisabled && selectOption(o.code as SubjectCode)}
                  className={[
                    'cursor-pointer px-3 py-2 text-sm transition-colors',
                    isActive    ? 'bg-primary-50 text-primary-800' : '',
                    isSelected  ? 'font-semibold text-primary-700' : 'text-gray-800',
                    isDisabled  ? 'cursor-not-allowed text-gray-400 line-through' : '',
                  ].join(' ')}
                >
                  {o.label}
                </li>
              );
            })
          )}
        </ul>
      )}
    </div>
  );
}
