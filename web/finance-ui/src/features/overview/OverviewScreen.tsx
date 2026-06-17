import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { Account, MonthlyTrend, SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { DASHBOARD_LIMITS } from '../../config/thresholds';
import { formatMoney } from '../../lib/formatMoney';

interface OverviewData {
  accounts: Account[];
  spending: SpendingRow[];
  trend: MonthlyTrend[];
}

function sumByCurrency<T>(rows: T[], getCurrency: (row: T) => string, getAmount: (row: T) => number) {
  return rows.reduce<Record<string, number>>((totals, row) => {
    const currency = getCurrency(row);
    totals[currency] = (totals[currency] ?? 0) + getAmount(row);
    return totals;
  }, {});
}

function maxAmount(rows: SpendingRow[]) {
  return Math.max(1, ...rows.map((row) => row.amount));
}

export function OverviewScreen() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [accounts, spending, trend] = await Promise.all([
          apiGet<Account[]>('/accounts'),
          apiGet<SpendingRow[]>('/transactions/spending?period=this_month&exclude_uncategorized=true'),
          apiGet<MonthlyTrend[]>(`/transactions/trend?months=${DASHBOARD_LIMITS.trendMonths}`),
        ]);
        if (!cancelled) {
          setData({ accounts, spending, trend });
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : 'Unknown error');
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const balanceByCurrency = useMemo(
    () => sumByCurrency(data?.accounts ?? [], (account) => account.currency, (account) => account.balance),
    [data?.accounts],
  );
  const spendByCurrency = useMemo(
    () => sumByCurrency(data?.spending ?? [], (row) => row.currency, (row) => row.amount),
    [data?.spending],
  );
  const topCategories = useMemo(
    () => [...(data?.spending ?? [])].sort((a, b) => b.amount - a.amount).slice(0, DASHBOARD_LIMITS.topCategoryRows),
    [data?.spending],
  );
  const categoryMax = maxAmount(topCategories);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section>
      <h1>Overview</h1>

      <Card title="Balance">
        {Object.entries(balanceByCurrency).length === 0 ? (
          <EmptyState>No accounts synced yet.</EmptyState>
        ) : (
          Object.entries(balanceByCurrency).map(([currency, amount]) => (
            <div className="metric-row" key={currency}>
              <span>{currency}</span>
              <strong>{formatMoney(amount, currency)}</strong>
            </div>
          ))
        )}
      </Card>

      <Card title="This month spend">
        {Object.entries(spendByCurrency).length === 0 ? (
          <EmptyState>No spending yet.</EmptyState>
        ) : (
          Object.entries(spendByCurrency).map(([currency, amount]) => (
            <div className="metric-row" key={currency}>
              <span>{currency}</span>
              <strong>{formatMoney(amount, currency)}</strong>
            </div>
          ))
        )}
      </Card>

      <Card title="Top categories">
        {topCategories.length === 0 ? (
          <EmptyState>No categories yet.</EmptyState>
        ) : (
          topCategories.map((row) => (
            <div className="bar-row" key={`${row.category}-${row.currency}`}>
              <div className="bar-row-label">
                <span>{row.category}</span>
                <strong>{formatMoney(row.amount, row.currency)}</strong>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${Math.round((row.amount / categoryMax) * 100)}%` }} />
              </div>
            </div>
          ))
        )}
      </Card>

      <Card title="Trend">
        {data.trend.length === 0 ? (
          <EmptyState>No trend data.</EmptyState>
        ) : (
          data.trend.map((row) => (
            <div className="metric-row" key={`${row.month}-${row.currency}`}>
              <span>{row.month} · {row.currency}</span>
              <strong>{formatMoney(row.income, row.currency)} / {formatMoney(row.expenses, row.currency)}</strong>
            </div>
          ))
        )}
      </Card>
    </section>
  );
}
