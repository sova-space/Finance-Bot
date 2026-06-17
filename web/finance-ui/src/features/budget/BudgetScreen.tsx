import { useEffect, useState } from 'react';

import { apiGet } from '../../api/client';
import type { BudgetRow, Pocket } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { DASHBOARD_LIMITS } from '../../config/thresholds';
import { formatMoney } from '../../lib/formatMoney';

interface BudgetData {
  budgets: BudgetRow[];
  pockets: Pocket[];
}

function ratioTone(ratio: number) {
  if (ratio >= DASHBOARD_LIMITS.budgetDangerRatio) return 'danger';
  if (ratio >= DASHBOARD_LIMITS.budgetWarningRatio) return 'warning';
  return 'default';
}

export function BudgetScreen() {
  const [data, setData] = useState<BudgetData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [budgets, pockets] = await Promise.all([
          apiGet<BudgetRow[]>('/budgets'),
          apiGet<Pocket[]>('/pockets'),
        ]);
        if (!cancelled) setData({ budgets, pockets });
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
      <h1>Budget</h1>
      <Card title="Pockets">
        {data.pockets.length === 0 ? <EmptyState>No pockets yet.</EmptyState> : null}
        {data.pockets.map((pocket) => {
          const ratio = pocket.monthly_budget > 0 ? Math.min(pocket.balance / pocket.monthly_budget, 1) : 0;
          return (
            <div className="bar-row" key={pocket.id}>
              <div className="bar-row-label">
                <span>{pocket.emoji ? `${pocket.emoji} ` : ''}{pocket.category}</span>
                <strong>{formatMoney(pocket.balance, pocket.currency)}</strong>
              </div>
              <div className="bar-track">
                <div className={`bar-fill ${ratioTone(ratio)}`} style={{ width: `${Math.round(ratio * 100)}%` }} />
              </div>
            </div>
          );
        })}
      </Card>
      <Card title="Limits">
        {data.budgets.length === 0 ? <EmptyState>No budget limits yet.</EmptyState> : null}
        {data.budgets.map((budget) => {
          const ratio = budget.limit > 0 ? Math.min(budget.spent / budget.limit, 1) : 0;
          return (
            <div className="bar-row" key={`${budget.category}-${budget.currency}`}>
              <div className="bar-row-label">
                <span>{budget.category}</span>
                <strong>{formatMoney(budget.spent, budget.currency)} / {formatMoney(budget.limit, budget.currency)}</strong>
              </div>
              <div className="bar-track">
                <div className={`bar-fill ${ratioTone(ratio)}`} style={{ width: `${Math.round(ratio * 100)}%` }} />
              </div>
            </div>
          );
        })}
      </Card>
    </section>
  );
}
