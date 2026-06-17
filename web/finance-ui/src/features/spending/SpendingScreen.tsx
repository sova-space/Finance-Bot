import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { formatMoney } from '../../lib/formatMoney';

function maxAmount(rows: SpendingRow[]) {
  return Math.max(1, ...rows.map((row) => row.amount));
}

export function SpendingScreen() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [rows, setRows] = useState<SpendingRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    setError(null);
    async function load() {
      try {
        const data = await apiGet<SpendingRow[]>(`/transactions/spending?period=${period}&exclude_uncategorized=false`);
        if (!cancelled) setRows(data);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const sortedRows = useMemo(() => [...(rows ?? [])].sort((a, b) => b.amount - a.amount), [rows]);
  const max = maxAmount(sortedRows);

  return (
    <section>
      <h1>Spending</h1>
      <PeriodSelector value={period} onChange={setPeriod} />
      {error ? <ErrorState message={error} /> : null}
      {!rows && !error ? <LoadingState /> : null}
      {rows ? (
        <Card>
          {sortedRows.length === 0 ? (
            <EmptyState>No spending for this period.</EmptyState>
          ) : (
            sortedRows.map((row) => (
              <div className={row.category === 'Uncategorized' ? 'bar-row muted' : 'bar-row'} key={`${row.category}-${row.currency}`}>
                <div className="bar-row-label">
                  <span>{row.category}</span>
                  <strong>{formatMoney(row.amount, row.currency)}</strong>
                </div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${Math.round((row.amount / max) * 100)}%` }} />
                </div>
              </div>
            ))
          )}
        </Card>
      ) : null}
    </section>
  );
}
