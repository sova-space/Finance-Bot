import { useEffect, useState } from 'react';

import { apiGet } from '../../api/client';
import type { ForecastRow, Goal } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { formatMoney } from '../../lib/formatMoney';

interface PlanData {
  goals: Goal[];
  forecast: ForecastRow[];
}

export function PlanScreen() {
  const [data, setData] = useState<PlanData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [goals, forecast] = await Promise.all([
          apiGet<Goal[]>('/goals'),
          apiGet<ForecastRow[]>('/forecast'),
        ]);
        if (!cancelled) setData({ goals, forecast });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section>
      <h1>Plan</h1>
      <Card title="Goals">
        {data.goals.length === 0 ? <EmptyState>No goals yet.</EmptyState> : null}
        {data.goals.map((goal) => (
          <div className="metric-row" key={goal.id}>
            <span>{goal.name}</span>
            <strong>{formatMoney(goal.current_amount, goal.currency)} / {formatMoney(goal.target_amount, goal.currency)}</strong>
          </div>
        ))}
      </Card>
      <Card title="Forecast">
        {data.forecast.length === 0 ? <EmptyState>No forecast yet.</EmptyState> : null}
        {data.forecast.slice(0, 8).map((row, index) => (
          <div className="metric-row" key={`${row.date ?? 'row'}-${index}`}>
            <span>{row.label ?? row.date ?? 'Forecast'}</span>
            <strong>{formatMoney(row.amount ?? row.balance ?? 0, row.currency)}</strong>
          </div>
        ))}
      </Card>
    </section>
  );
}
