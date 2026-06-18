import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { BudgetRow, FxRate, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, preferredCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { CashflowDiagram } from '../overview/CashflowDiagram';
import { buildCashflowSummary, jarForCategory, spendingRowsFromTransactions, type CashflowJarId } from './model';

interface CashflowData {
  budgets: BudgetRow[];
  rates: FxRate[];
  transactions: TransactionItem[];
}

function ratioTone(ratio: number | null) {
  if (ratio === null) return 'default';
  if (ratio >= 1) return 'danger';
  if (ratio >= 0.8) return 'warning';
  return 'default';
}

function periodLabel(period: AnalyticsPeriod) {
  return period.replace('_', ' ');
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
        const [transactions, budgets, rates] = await Promise.all([
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
          apiGet<BudgetRow[]>('/budgets').catch(() => []),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
        ]);
        if (!cancelled) setData({ transactions, budgets, rates });
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
  const jarChartRows = useMemo(
    () => summary.jars.filter((jar) => jar.spent > 0).map((jar) => ({ category: jar.label, currency: jar.currency, amount: jar.spent })),
    [summary.jars],
  );
  const visibleCategories = selectedJar === 'all' ? summary.categories : summary.categories.filter((row) => row.jarId === selectedJar);
  const visibleTransactions = summary.recentTransactions.filter((tx) => selectedJar === 'all' || jarForCategory(tx.category).id === selectedJar);
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
          description={`Where money goes · budget pressure · ${periodLabel(period)} · ${chartCurrency}`}
          meta={<SovaBadge tone={summary.budgetRemaining !== null && summary.budgetRemaining < 0 ? 'bad' : 'accent'}>{budgetStatus}</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: 'Income', value: formatCompactMoney(summary.income, chartCurrency), hint: 'clean positive tx', tone: 'good' },
            { label: 'Spent', value: formatCompactMoney(summary.spent, chartCurrency), hint: `${summary.categories.length} categories`, tone: 'warn' },
            { label: 'Left', value: formatCompactMoney(summary.leftAfterSpend, chartCurrency), hint: 'income minus spend', tone: summary.leftAfterSpend >= 0 ? 'accent' : 'warn' },
            { label: 'Needs sorting', value: summary.needsSorting ? formatCompactMoney(summary.needsSorting, chartCurrency) : '0', hint: 'uncategorized', tone: summary.needsSorting ? 'neutral' : 'good' },
          ]}
        />
      </div>

      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Spending</p>
          <h2>Money groups</h2>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      <div className="cashflow-report-grid">
        <Card className="wide cashflow-card" title="Where money went" subtitle="Fixed / Flexible / Non-monthly">
          <CashflowDiagram categories={jarChartRows} currency={chartCurrency} expenses={summary.spent} />
        </Card>

        <Card title="Budget pressure" subtitle="from category limits">
          <div className="jar-list">
            {summary.jars.map((jar, index) => {
              const ratio = jar.ratio === null ? 0 : Math.min(jar.ratio, 1);
              return (
                <button
                  className={`jar-row ${selectedJar === jar.id ? 'active' : ''}`}
                  key={jar.id}
                  onClick={() => setSelectedJar(selectedJar === jar.id ? 'all' : jar.id)}
                  type="button"
                >
                  <span className="jar-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <div>
                    <strong>{jar.label}</strong>
                    <small>{jar.hint}</small>
                  </div>
                  <em>{formatCompactMoney(jar.spent, chartCurrency)}</em>
                  <div className="jar-track">
                    <span className={`bar-fill ${ratioTone(jar.ratio)}`} style={{ width: `${Math.round(ratio * 100)}%` }} />
                  </div>
                  <small className="jar-limit">
                    {jar.limit > 0 ? `${formatCompactMoney(jar.spent, chartCurrency)} / ${formatCompactMoney(jar.limit, chartCurrency)}` : 'no limit'}
                  </small>
                </button>
              );
            })}
          </div>
          <button className="soft-button cashflow-clear" onClick={() => setSelectedJar('all')} type="button">All jars</button>
        </Card>

        <Card className="wide" title="Categories" subtitle={selectedJar === 'all' ? 'All jars' : summary.jars.find((jar) => jar.id === selectedJar)?.label}>
          {visibleCategories.length === 0 ? (
            <EmptyState>No spending for this view.</EmptyState>
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
                  <span className="category-pill">{jarForCategory(tx.category).label}</span>
                  <em className={tx.amount > 0 ? 'positive' : ''}>{formatMoney(tx.amount, tx.currency)}</em>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}
