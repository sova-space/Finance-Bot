import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { Account, FxRate, SpendingRow, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import type { AnalyticsPeriod } from '../../config/periods';
import { lightFeedback } from '../../lib/runtime';
import { CHART_COLORS, convertAmount, preferredCurrency, rowsForCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { CashflowDiagram } from './CashflowDiagram';

interface OverviewData {
  accounts: Account[];
  rates: FxRate[];
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

function spendingRowsFromTransactions(transactions: TransactionItem[]): SpendingRow[] {
  const totals = new Map<string, SpendingRow>();

  transactions
    .filter((tx) => tx.amount < 0 && !tx.is_pending && !isInternalTransfer(tx))
    .forEach((tx) => {
      const category = tx.category ?? 'Uncategorized';
      const key = `${category}:${tx.currency}`;
      const existing = totals.get(key) ?? { category, currency: tx.currency, amount: 0 };
      existing.amount += Math.abs(tx.amount);
      totals.set(key, existing);
    });

  return [...totals.values()].sort((a, b) => b.amount - a.amount);
}

function periodSubtitle(period: AnalyticsPeriod) {
  const now = new Date();
  if (period === 'this_year') return String(now.getFullYear());
  if (period === 'last_90d') return 'last 90 days';
  return now.toLocaleDateString('en', { month: 'long', year: 'numeric' });
}

function CashflowRangeMenu({ value, onChange }: { value: AnalyticsPeriod; onChange: (period: AnalyticsPeriod) => void }) {
  const items: Array<{ id: AnalyticsPeriod; label: string }> = [
    { id: 'this_month', label: 'Month' },
    { id: 'last_90d', label: 'Quarter' },
  ];

  return (
    <div className="cashflow-date-selector" aria-label="Cashflow date range">
      <span>Date range</span>
      <div>
        {items.map((item) => (
          <button
            className={item.id === value ? 'active' : ''}
            key={item.id}
            onClick={() => {
              lightFeedback();
              onChange(item.id);
            }}
            type="button"
          >
            <strong>{item.label}</strong>
            <small>{periodSubtitle(item.id)}</small>
          </button>
        ))}
      </div>
    </div>
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
        const [accounts, rates, transactions] = await Promise.all([
          apiGet<Account[]>('/accounts'),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
        ]);
        if (!cancelled) {
          setData({ accounts, rates, transactions });
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
    () => spendingRowsFromTransactions(data?.transactions ?? []),
    [data?.transactions],
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
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow="finance"
          title="Money overview"
          description={`Cashflow, categories, and recent transactions · ${periodSubtitle(period)} · ${chartCurrency}`}
          meta={<SovaBadge tone="accent">{data.accounts.length} accounts</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: 'Net balance', value: data.accounts.length === 0 ? '—' : formatCompactMoney(convertedBalance, chartCurrency), hint: chartCurrency, tone: 'accent' },
            { label: 'Spent', value: formatCompactMoney(currentMonthSpend, chartCurrency), hint: biggestCategory ? `${biggestCategory.category} leads` : 'No spending yet', tone: 'warn' },
            { label: 'Top category', value: biggestCategory?.category ?? '—', hint: biggestCategory ? formatMoney(biggestCategory.amount, biggestCategory.currency) : 'No categories yet', tone: 'good' },
            { label: 'Transactions', value: recentTransactions.length, hint: 'internal transfers hidden', tone: 'neutral' },
          ]}
        />
      </div>

      <div className="analytics-grid overview-grid">
        <Card className="chart-card wide cashflow-card" title="Cashflow" subtitle={`Spending flow · ${chartCurrency}`}>
          <div className="card-inline-toolbar">
            <CashflowRangeMenu value={period} onChange={setPeriod} />
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
