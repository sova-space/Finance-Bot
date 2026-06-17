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

const INTERNAL_CATEGORIES = new Set(['Income', 'Cashback', 'Couple Transfer', 'Partner', 'Finance']);

function sumByCurrency<T>(rows: T[], getCurrency: (row: T) => string, getAmount: (row: T) => number) {
  return rows.reduce<Record<string, number>>((totals, row) => {
    const currency = getCurrency(row);
    totals[currency] = (totals[currency] ?? 0) + getAmount(row);
    return totals;
  }, {});
}

function isInternalTransfer(tx: TransactionItem) {
  const category = tx.category ?? '';
  const description = tx.description.toLowerCase();
  return (
    INTERNAL_CATEGORIES.has(category) ||
    description.includes('transfer') ||
    description.includes('переказ') ||
    description.includes('поповнення')
  );
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

  const spendingRows = useMemo(
    () => (data?.spending ?? []).filter((row) => !INTERNAL_CATEGORIES.has(row.category)),
    [data?.spending],
  );
  const rawSpendByCurrency = useMemo(
    () => sumByCurrency(spendingRows, (row) => row.currency, (row) => row.amount),
    [spendingRows],
  );
  const chartCurrency = useMemo(() => preferredCurrency(spendingRows, currency), [currency, spendingRows]);
  const convertedBalance = useMemo(
    () =>
      (data?.accounts ?? []).reduce(
        (sum, account) => sum + convertAmount(account.balance, account.currency, chartCurrency, data?.rates ?? []),
        0,
      ),
    [chartCurrency, data?.accounts, data?.rates],
  );
  const topCategories = useMemo(
    () => rowsForCurrency(spendingRows, chartCurrency, data?.rates ?? []).slice(0, 12),
    [chartCurrency, data?.rates, spendingRows],
  );
  const transactions = useMemo(
    () => (data?.transactions ?? []).filter((tx) => !isInternalTransfer(tx)),
    [data?.transactions],
  );
  const recentTransactions = transactions.slice(0, 12);
  const totalSpend = topCategories.reduce((sum, row) => sum + row.amount, 0);
  const currentMonthSpend = data?.rates.length ? totalSpend : (rawSpendByCurrency[chartCurrency] ?? totalSpend);
  const biggestCategory = topCategories[0];

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page overview-only-page">
      <div className="hero-grid overview-hero-grid">
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

        <Card className="kpi-card" title="Top category" subtitle="Current period">
          <strong>{biggestCategory?.category ?? '—'}</strong>
          <span>{biggestCategory ? formatMoney(biggestCategory.amount, biggestCategory.currency) : 'No categories yet'}</span>
        </Card>
      </div>

      <div className="analytics-grid overview-grid">
        <Card className="chart-card wide cashflow-card" title="Cashflow" subtitle={`Spending flow · ${chartCurrency}`}>
          <div className="card-inline-toolbar">
            <PeriodSelector value={period} onChange={setPeriod} />
          </div>
          <CashflowDiagram categories={topCategories} currency={chartCurrency} expenses={currentMonthSpend} />
        </Card>

        <Card className="chart-card category-pocket-card" title="Categories" subtitle="Current period">
          {topCategories.length === 0 ? (
            <EmptyState>No category data.</EmptyState>
          ) : (
            <div className="category-board">
              {topCategories.map((row, index) => {
                const share = totalSpend > 0 ? Math.round((row.amount / totalSpend) * 100) : 0;
                return (
                  <div className="category-tile" key={row.category}>
                    <div className="category-rank" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }}>{index + 1}</div>
                    <div className="category-body">
                      <div className="category-mainline">
                        <strong>{row.category}</strong>
                        <em>{formatCompactMoney(row.amount, row.currency)}</em>
                      </div>
                      <div className="category-meta"><span>{share}% of spending</span></div>
                      <div className="category-rail">
                        <div style={{ width: `${share}%`, background: CHART_COLORS[index % CHART_COLORS.length] }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="wide transactions-bottom-card" title="Transactions" subtitle={`${recentTransactions.length} recent · internal transfers hidden`}>
          {recentTransactions.length === 0 ? (
            <EmptyState>No transactions for this period.</EmptyState>
          ) : (
            <div className="overview-transaction-list">
              {recentTransactions.map((tx, index) => {
                const converted = convertAmount(tx.amount, tx.currency, chartCurrency, data.rates);
                return (
                  <div className="overview-transaction-row" key={`${tx.date}-${tx.description}-${index}`}>
                    <div>
                      <strong>{tx.description}</strong>
                      <span>{tx.category ?? 'Uncategorized'} · {tx.date}</span>
                    </div>
                    <em className={converted >= 0 ? 'positive' : ''}>{formatMoney(converted, chartCurrency)}</em>
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
