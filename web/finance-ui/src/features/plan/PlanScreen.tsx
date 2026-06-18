import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { ForecastRow, Goal } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';

interface PlanData {
  goals: Goal[];
  forecast: ForecastRow[];
}

function goalProgress(goal: Goal) {
  if (goal.target_amount <= 0) return 0;
  return Math.min(100, Math.round((goal.current_amount / goal.target_amount) * 100));
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

  const primaryCurrency = data?.goals[0]?.currency ?? data?.forecast[0]?.currency ?? 'UAH';
  const sameCurrencyGoals = data?.goals.filter((goal) => goal.currency === primaryCurrency) ?? [];
  const totals = useMemo(() => {
    const target = sameCurrencyGoals.reduce((sum, goal) => sum + goal.target_amount, 0);
    const saved = sameCurrencyGoals.reduce((sum, goal) => sum + goal.current_amount, 0);
    return { target, saved, left: Math.max(0, target - saved), progress: target > 0 ? Math.round((saved / target) * 100) : 0 };
  }, [sameCurrencyGoals]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page goals-page">
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow="finance"
          title="Goals"
          description={`What I am saving and planning for · ${primaryCurrency}`}
          meta={<SovaBadge tone="accent">{data.goals.length} goals</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: 'Target', value: formatCompactMoney(totals.target, primaryCurrency), hint: 'planned buys', tone: 'accent' },
            { label: 'Saved', value: formatCompactMoney(totals.saved, primaryCurrency), hint: `${totals.progress}%`, tone: 'good' },
            { label: 'Left', value: formatCompactMoney(totals.left, primaryCurrency), hint: 'to fund', tone: 'neutral' },
          ]}
        />
      </div>

      <div className="analytics-grid goals-grid">
        <Card className="wide" title="Planned purchases" subtitle="Savings targets and progress">
          {data.goals.length === 0 ? <EmptyState>No goals yet.</EmptyState> : null}
          <div className="goal-list">
            {data.goals.map((goal) => {
              const progress = goalProgress(goal);
              const left = Math.max(0, goal.target_amount - goal.current_amount);
              return (
                <div className="goal-row" key={goal.id}>
                  <div>
                    <strong>{goal.name}</strong>
                    <span>{goal.deadline ? `Deadline ${goal.deadline}` : 'No deadline'}</span>
                  </div>
                  <div className="goal-progress">
                    <div className="goal-track"><span style={{ width: `${progress}%` }} /></div>
                    <small>{progress}% · {formatMoney(left, goal.currency)} left</small>
                  </div>
                  <em>{formatMoney(goal.current_amount, goal.currency)} / {formatMoney(goal.target_amount, goal.currency)}</em>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="Affordability" subtitle="Forecast signal">
          {data.forecast.length === 0 ? <EmptyState>No forecast yet.</EmptyState> : null}
          <div className="summary-list">
            {data.forecast.slice(0, 8).map((row, index) => (
              <div className="summary-row" key={`${row.date ?? 'row'}-${index}`}>
                <span>{row.label ?? row.date ?? 'Forecast'}</span>
                <strong>{formatMoney(row.amount ?? row.balance ?? 0, row.currency ?? primaryCurrency)}</strong>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
}
