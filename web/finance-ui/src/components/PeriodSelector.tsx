import { ANALYTICS_PERIODS, type AnalyticsPeriod } from '../config/periods';
import { lightFeedback } from '../lib/runtime';

interface PeriodSelectorProps {
  value: AnalyticsPeriod;
  onChange: (period: AnalyticsPeriod) => void;
}

export function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <div className="period-selector" aria-label="Analytics period">
      {ANALYTICS_PERIODS.map((period) => (
        <button
          className={period.id === value ? 'active' : ''}
          key={period.id}
          onClick={() => {
            lightFeedback();
            onChange(period.id);
          }}
          type="button"
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}
