import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { Account, FxRate, SpendingRow, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, convertAmount, preferredCurrency, rowsForCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { CashflowDiagram } from './CashflowDiagram';

interface OverviewData {
  accounts: Account[];
  rates: FxRate[];
  spending: SpendingRow[];
  transactions: TransactionItem[];
}

function sumByCurrency<T>(rows: T[], getCurrency: (row: T) => string, getAmount: (row: T) => number) {
  return rows.reduce<Record<string, number>>((totals, row) => {
    const currency = getCurrency(row);
    totals[currency] = (totals[currency] ?? 0) + getAmount(row);
    return totals;
  }, {});
}

export function OverviewScreen() {
  const { currency } = usePreferences();
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [accounts, rates, spending, transactions] = await Promise.all([
          apiGet<Account[]>('/accounts'),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<SpendingRow[]>(`/transactions/spending?period=${period}&exclude_uncategorized=true`),
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
        ]);
        if (!cancelled) {
          setData({ accounts, rates, spending, transactions });
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
  }, [period]);

  const rawSpendByCurrency = useMemo(
    () => sumByCurrency(data?.spending ?? [], (row) => row.currency, (row) => row.amount),
    [data?.spending],
  );
  const chartCurrency = useMemo(() => preferredCurrency(data?.spending ?? [], currency), [currency, data?.spending]);
  const convertedBalance = useMemo(
    () =>
      (data?.accounts ?? []).reduce(
        (sum, account) => sum + convertAmount(account.balance, account.currency, chartCurrency, data?.rates ?? []),
        0,
      ),
    [chartCurrency, data?.accounts, data?.rates],
  );
  const topCategories = useMemo(
    () => rowsForCurrency(data?.spending ?? [], chartCurrency, data?.rates ?? []).slice(0, 12),
    [chartCurrency, data?.rates, data?.spending],
  );
  const periodIncome = useMemo(
    () =>
      (data?.transactions ?? [])
        .filter((row) => row.amount > 0)
        .reduce((sum, row) => sum + convertAmount(row.amount, row.currency, chartCurrency, data?.rates ?? []), 0),
    [chartCurrency, data?.rates, data?.transactions],
  );
  const recentTransactions = useMemo(() => (data?.transactions ?? []).slice(0, 6), [data?.transactions]);
  const totalSpend = topCategories.reduce((sum, row) => sum + row.amount, 0);
  const currentMonthSpend = data?.rates.length ? totalSpend : (rawSpendByCurrency[chartCurrency] ?? totalSpend);
  const biggestCategory = topCategories[0];

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page">
      <div className="hero-grid">
        <Card tone="dark" className="hero-card">
          <p className="eyebrow">Net balance</p>
          {data.accounts.length === 0 ? (
            <EmptyState>No accounts synced yet.</EmptyState>
          ) : (
            <div className="hero-metrics single">
              <div>
                <span>{chartCurrency}</span>
                <strong>{formatMoney(convertedBalance, chartCurrency)}</strong>
              </div>
            </div>
          )}
        </Card>

        <Card className="kpi-card" title="Spent" subtitle={`${period.replace('_', ' ')} · ${chartCurrency}${data.rates.length ? ' · converted' : ''}`}>
          <strong>{formatCompactMoney(currentMonthSpend, chartCurrency)}</strong>
          <span>{biggestCategory ? `${biggestCategory.category} leads spend` : 'No spending yet'}</span>
        </Card>

        <Card className="kpi-card" title="Top category" subtitle="Current month">
          <strong>{biggestCategory?.category ?? '—'}</strong>
          <span>{biggestCategory ? formatMoney(biggestCategory.amount, biggestCategory.currency) : 'No categories yet'}</span>
        </Card>
      </div>

      <div className="analytics-grid">
        <Card className="chart-card wide cashflow-card" title="Cashflow" subtitle={`Income → spending · ${chartCurrency}`}>
          <div className="card-inline-toolbar">
            <PeriodSelector value={period} onChange={setPeriod} />
          </div>
          <CashflowDiagram
            categories={topCategories}
            currency={chartCurrency}
            expenses={currentMonthSpend}
            income={periodIncome || currentMonthSpend}
          />
        </Card>

        <Card className="chart-card recent-card" title="Recent activity" subtitle={period.replace('_', ' ')}>
          {recentTransactions.length === 0 ? (
            <EmptyState>No transactions for this period.</EmptyState>
          ) : (
            <div className="recent-list">
              {recentTransactions.map((tx, index) => {
                const converted = convertAmount(tx.amount, tx.currency, chartCurrency, data.rates);
                return (
                  <div className="recent-row" key={`${tx.date}-${tx.description}-${index}`}>
                    <div>
                      <strong>{tx.description}</strong>
                      <span>{tx.category ?? tx.date}</span>
                    </div>
                    <em className={converted >= 0 ? 'positive' : ''}>{formatMoney(converted, chartCurrency)}</em>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="chart-card wide category-pocket-card" title="Category pockets" subtitle="Moneko-style spend buckets">
          {topCategories.length === 0 ? (
            <EmptyState>No category data.</EmptyState>
          ) : (
            <div className="pocket-grid">
              {topCategories.map((row, index) => {
                const share = totalSpend > 0 ? Math.round((row.amount / totalSpend) * 100) : 0;
                return (
                  <div className="pocket-card" key={row.category}>
                    <div className="pocket-topline">
                      <span className="pocket-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                      <strong>{row.category}</strong>
                      <em>{share}%</em>
                    </div>
                    <div className="pocket-amount">{formatCompactMoney(row.amount, row.currency)}</div>
                    <div className="pocket-track">
                      <div
                        className="pocket-fill"
                        style={{
                          width: `${share}%`,
                          background: CHART_COLORS[index % CHART_COLORS.length],
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}
