import { useTranslations } from 'next-intl';

interface ProgressBarProps {
  currentStep: 1 | 2 | 3;
  totalSteps?: number;
}

export function ProgressBar({ currentStep, totalSteps = 3 }: ProgressBarProps) {
  const t = useTranslations('intake');

  return (
    <nav aria-label={t('stepOf', { current: currentStep, total: totalSteps })}>
      <ol className="flex items-center gap-0" role="list">
        {([1, 2, 3] as const).map((step) => {
          const isCompleted = step < currentStep;
          const isCurrent   = step === currentStep;
          const label = t(`steps.${step}` as 'steps.1' | 'steps.2' | 'steps.3');

          return (
            <li key={step} className="flex flex-1 items-center">
              {/* Step circle */}
              <div className="flex flex-col items-center gap-1">
                <div
                  aria-current={isCurrent ? 'step' : undefined}
                  className={[
                    'flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-bold transition-colors',
                    isCompleted
                      ? 'border-primary-600 bg-primary-600 text-white'
                      : isCurrent
                      ? 'border-primary-600 bg-white text-primary-600'
                      : 'border-gray-300 bg-white text-gray-400',
                  ].join(' ')}
                >
                  {isCompleted ? (
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    step
                  )}
                </div>
                <span
                  className={[
                    'hidden text-xs sm:block',
                    isCurrent ? 'font-semibold text-primary-700' : 'text-gray-500',
                  ].join(' ')}
                >
                  {label}
                </span>
              </div>

              {/* Connector line (after all but last) */}
              {step < totalSteps && (
                <div
                  aria-hidden="true"
                  className={[
                    'h-0.5 flex-1 transition-colors',
                    step < currentStep ? 'bg-primary-600' : 'bg-gray-200',
                  ].join(' ')}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
