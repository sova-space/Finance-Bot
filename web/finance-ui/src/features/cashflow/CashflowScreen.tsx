import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { BudgetRow, FxRate, MonthlyTrend, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, convertAmount, preferredCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { buildCashflowSummary, jarForCategory, spendingRowsFromTransactions, type CashflowJarId } from './model';

interface CashflowData {
  budgets: BudgetRow[];
  rates: FxRate[];
  transactions: TransactionItem[];
  trend: MonthlyTrend[];
}

function ratioTone(ratio: number | null) {
  if (ratio === null) return 'default';
  if (ratio >= 1) return 'danger';
  if (ratio >= 0.8) return 'warning';
  return 'default';
}

function periodLabel(period: AnalyticsPeriod) {
  if (period === 'this_year') return 'year';
  if (period === 'last_90d') return 'quarter';
  return 'month';
}

export function CashflowScreen() {
  const { currency } = usePreferences();
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [selectedJar, setSelectedJar] = useState<CashflowJarId | 'all'>('all');
  const [data, setData] = useState<CashflowData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    async function load() {
      try {
        const [transactions, budgets, rates, trend] = await Promise.all([
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
          apiGet<BudgetRow[]>('/budgets').catch(() => []),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<MonthlyTrend[]>('/transactions/trend?months=12').catch(() => []),
        ]);
        if (!cancelled) setData({ transactions, budgets, rates, trend });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const spendingRows = useMemo(() => spendingRowsFromTransactions(data?.transactions ?? []), [data?.transactions]);
  const chartCurrency = useMemo(() => preferredCurrency(spendingRows, currency), [currency, spendingRows]);
  const summary = useMemo(
    () => buildCashflowSummary(data?.transactions ?? [], data?.budgets ?? [], data?.rates ?? [], chartCurrency),
    [chartCurrency, data?.budgets, data?.rates, data?.transactions],
  );
  const visibleCategories = selectedJar === 'all' ? summary.categories : summary.categories.filter((row) => row.jarId === selectedJar);
  const visibleTransactions = summary.recentTransactions.filter((tx) => selectedJar === 'all' || jarForCategory(tx.category).id === selectedJar);
  const monthlyTrend = useMemo(
    () => (data?.trend ?? []).map((row) => ({
      ...row,
      income: convertAmount(row.income, row.currency, chartCurrency, data?.rates ?? []),
      expenses: convertAmount(row.expenses, row.currency, chartCurrency, data?.rates ?? []),
      currency: chartCurrency,
    })),
    [chartCurrency, data?.rates, data?.trend],
  );
  const trendMax = Math.max(...monthlyTrend.flatMap((row) => [row.income, row.expenses]), 1);
  const budgetStatus = summary.budgetRemaining === null
    ? 'No limits yet'
    : summary.budgetRemaining >= 0
      ? `${formatCompactMoney(summary.budgetRemaining, chartCurrency)} left`
      : `${formatCompactMoney(Math.abs(summary.budgetRemaining), chartCurrency)} over`;

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page cashflow-page">
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow="finance"
          title="Spending"
          description={`Income, expenses, groups · ${periodLabel(period)} · ${chartCurrency}`}
          meta={<SovaBadge tone={summary.leftAfterSpend >= 0 ? 'good' : 'bad'}>{summary.leftAfterSpend >= 0 ? 'within income' : 'over income'}</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: 'Income', value: formatCompactMoney(summary.income, chartCurrency), hint: `${summary.incomeSources.length} sources`, tone: 'good' },
            { label: 'Expenses', value: formatCompactMoney(summary.spent, chartCurrency), hint: `${summary.categories.length} categories`, tone: 'warn' },
            { label: 'Left', value: formatCompactMoney(summary.leftAfterSpend, chartCurrency), hint: 'income - expenses', tone: summary.leftAfterSpend >= 0 ? 'accent' : 'warn' },
            { label: 'Needs sorting', value: summary.needsSorting ? formatCompactMoney(summary.needsSorting, chartCurrency) : '0', hint: 'uncategorized', tone: summary.needsSorting ? 'neutral' : 'good' },
          ]}
        />
      </div>

      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Range</p>
          <h2>Income and expenses</h2>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      <div className="cashflow-report-grid">
        <Card className="wide" title="Monthly picture" subtitle="Income, expenses, left">
          {monthlyTrend.length === 0 ? (
            <EmptyState>No trend yet.</EmptyState>
          ) : (
            <div className="trend-list">
              {monthlyTrend.slice(-12).map((row) => {
                const left = row.income - row.expenses;
                return (
                  <div className="trend-row" key={`${row.month}-${row.currency}`}>
                    <strong>{row.month}</strong>
                    <div className="trend-bars">
                      <span className="income" style={{ width: `${Math.max(4, (row.income / trendMax) * 100)}%` }} />
                      <span className="expense" style={{ width: `${Math.max(4, (row.expenses / trendMax) * 100)}%` }} />
                    </div>
                    <em className={left >= 0 ? 'positive-text' : 'danger-text'}>{formatMoney(left, row.currency)}</em>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="wide" title="Income sources" subtitle="Where money came from">
          {summary.incomeSources.length === 0 ? (
            <EmptyState>No income for this range.</EmptyState>
          ) : (
            <div className="cashflow-category-list">
              {summary.incomeSources.slice(0, 8).map((row, index) => (
                <div className="cashflow-category-row" key={row.name}>
                  <span className="cashflow-color income" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <div>
                    <strong>{row.name}</strong>
                    <small>{row.count} transactions</small>
                  </div>
                  <em>{formatMoney(row.amount, row.currency)}</em>
                  <small>{Math.round(row.share)}%</small>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="wide" title="Spending groups" subtitle="Normal groups, not budget rules">
          <div className="spending-group-grid">
            {summary.jars.map((jar, index) => {
              const active = selectedJar === jar.id;
              return (
                <button className={`spending-group-card ${active ? 'active' : ''}`} key={jar.id} onClick={() => setSelectedJar(active ? 'all' : jar.id)} type="button">
                  <span className="jar-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <strong>{jar.label}</strong>
                  <em>{formatCompactMoney(jar.spent, chartCurrency)}</em>
                  <small>{jar.hint} · {Math.round(jar.share)}%</small>
                </button>
              );
            })}
          </div>
          <button className="soft-button cashflow-clear" onClick={() => setSelectedJar('all')} type="button">All groups</button>
        </Card>

        <Card className="wide" title="Where money went" subtitle={selectedJar === 'all' ? 'All groups' : summary.jars.find((jar) => jar.id === selectedJar)?.label}>
          {visibleCategories.length === 0 ? (
            <EmptyState>No spending for this range.</EmptyState>
          ) : (
            <div className="cashflow-category-list">
              {visibleCategories.map((row, index) => (
                <div className="cashflow-category-row" key={`${row.category}-${row.currency}`}>
                  <span className="cashflow-color" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <div>
                    <strong>{row.category}</strong>
                    <small>{row.jarLabel}</small>
                  </div>
                  <em>{formatMoney(row.amount, row.currency)}</em>
                  <small>{Math.round(row.share)}%</small>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Transactions" subtitle="recent, cleaned">
          {visibleTransactions.length === 0 ? (
            <EmptyState>No transactions.</EmptyState>
          ) : (
            <div className="transaction-mini-table">
              {visibleTransactions.slice(0, 10).map((tx, index) => (
                <div className="mini-tx-row" key={`${tx.date}-${tx.description}-${index}`}>
                  <div>
                    <strong>{tx.description}</strong>
                    <span>{tx.category ?? 'Uncategorized'} · {tx.date}</span>
                  </div>
                  <span className="category-pill">{tx.amount > 0 ? 'Income' : jarForCategory(tx.category).label}</span>
                  <em className={tx.amount > 0 ? 'positive' : ''}>{formatMoney(tx.amount, tx.currency)}</em>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="wide" title="Budget pressure" subtitle="monthly limits by group">
          <div className="jar-list">
            {summary.jars.map((jar, index) => {
              const ratio = jar.ratio === null ? 0 : Math.min(jar.ratio, 1);
              return (
                <div className="jar-row static" key={jar.id}>
                  <span className="jar-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <div>
                    <strong>{jar.label}</strong>
                    <small>{jar.limit > 0 ? `${formatCompactMoney(jar.remaining ?? 0, chartCurrency)} left` : 'no limit'}</small>
                  </div>
                  <em>{formatCompactMoney(jar.spent, chartCurrency)}</em>
                  <div className="jar-track">
                    <span className={`bar-fill ${ratioTone(jar.ratio)}`} style={{ width: `${Math.round(ratio * 100)}%` }} />
                  </div>
                  <small className="jar-limit">
                    {jar.limit > 0 ? `${formatCompactMoney(jar.spent, chartCurrency)} / ${formatCompactMoney(jar.limit, chartCurrency)}` : 'set budgets to use pressure'}
                  </small>
                </div>
              );
            })}
          </div>
          <div className="accounts-net-reference"><span>Total</span><strong>{budgetStatus}</strong><em>budgeting section</em></div>
        </Card>
      </div>
    </section>
  );
}
