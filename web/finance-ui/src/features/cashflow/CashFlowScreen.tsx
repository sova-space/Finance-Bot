import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { FxRate, SpendingRow, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, convertAmount, preferredCurrency, rowsForCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { CashflowDiagram } from '../overview/CashflowDiagram';

interface CashFlowData {
  rates: FxRate[];
  spending: SpendingRow[];
  transactions: TransactionItem[];
}

function periodLabel(period: AnalyticsPeriod) {
  return period.replace('_', ' ');
}

function safeSavingsRate(income: number, net: number) {
  if (income <= 0) return 0;
  return Math.round((net / income) * 1000) / 10;
}

export function CashFlowScreen() {
  const { currency } = usePreferences();
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [data, setData] = useState<CashFlowData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    async function load() {
      try {
        const [rates, spending, transactions] = await Promise.all([
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<SpendingRow[]>(`/transactions/spending?period=${period}&exclude_uncategorized=true`),
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
        ]);
        if (!cancelled) setData({ rates, spending, transactions });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const chartCurrency = useMemo(() => preferredCurrency(data?.spending ?? [], currency), [currency, data?.spending]);
  const categories = useMemo(
    () => rowsForCurrency(data?.spending ?? [], chartCurrency, data?.rates ?? []),
    [chartCurrency, data?.rates, data?.spending],
  );
  const expenses = categories.reduce((sum, row) => sum + row.amount, 0);
  const income = useMemo(
    () =>
      (data?.transactions ?? [])
        .filter((tx) => tx.amount > 0)
        .reduce((sum, tx) => sum + convertAmount(tx.amount, tx.currency, chartCurrency, data?.rates ?? []), 0),
    [chartCurrency, data?.rates, data?.transactions],
  );
  const net = income - expenses;
  const savingsRate = safeSavingsRate(income, net);
  const largestCategory = categories[0];
  const outgoingRows = categories.slice(0, 8);

  return (
    <section className="dashboard-page monarch-page">
      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Reports</p>
          <h2>Income to spending</h2>
        </div>
        <div className="toolbar-row">
          <PeriodSelector value={period} onChange={setPeriod} />
          <button className="soft-button" type="button">Filters</button>
          <button className="soft-button" type="button">Share</button>
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}
      {!data && !error ? <LoadingState /> : null}
      {data ? (
        <>
          <div className="metric-strip">
            <Card className="monarch-metric" title="Total income" subtitle={periodLabel(period)}>
              <strong className="positive-text">{formatCompactMoney(income, chartCurrency)}</strong>
            </Card>
            <Card className="monarch-metric" title="Total expenses" subtitle={periodLabel(period)}>
              <strong>{formatCompactMoney(expenses, chartCurrency)}</strong>
            </Card>
            <Card className="monarch-metric" title="Total net income" subtitle={net >= 0 ? 'Saved' : 'Overspent'}>
              <strong className={net >= 0 ? 'positive-text' : 'danger-text'}>{formatCompactMoney(net, chartCurrency)}</strong>
            </Card>
            <Card className="monarch-metric" title="Savings rate" subtitle="Income kept">
              <strong className={savingsRate >= 0 ? 'positive-text' : 'danger-text'}>{savingsRate}%</strong>
            </Card>
          </div>

          <div className="analytics-grid monarch-grid">
            <Card className="chart-card wide cashflow-card" title="Cash flow" subtitle={`${periodLabel(period)} · by category & group`}>
              <CashflowDiagram categories={categories} currency={chartCurrency} expenses={expenses} income={income || expenses} />
            </Card>

            <Card className="chart-card" title="Summary" subtitle={chartCurrency}>
              <div className="summary-list">
                <div className="summary-row"><span>Top category</span><strong>{largestCategory?.category ?? '—'}</strong></div>
                <div className="summary-row"><span>Largest flow</span><strong>{largestCategory ? formatMoney(largestCategory.amount, chartCurrency) : '—'}</strong></div>
                <div className="summary-row"><span>Categories</span><strong>{categories.length}</strong></div>
                <div className="summary-row"><span>Transactions</span><strong>{data.transactions.length}</strong></div>
                <div className="summary-row"><span>Status</span><strong>{net >= 0 ? 'Surplus' : 'Deficit'}</strong></div>
              </div>
            </Card>

            <Card className="wide" title="Where money went" subtitle="Chart drilldown">
              {outgoingRows.length === 0 ? (
                <EmptyState>No spending categories yet.</EmptyState>
              ) : (
                <div className="flow-breakdown">
                  {outgoingRows.map((row, index) => {
                    const share = expenses > 0 ? Math.round((row.amount / expenses) * 100) : 0;
                    return (
                      <div className="flow-row" key={row.category}>
                        <div className="flow-label">
                          <i style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                          <strong>{row.category}</strong>
                          <span>{share}%</span>
                        </div>
                        <div className="flow-track"><div style={{ width: `${share}%`, background: CHART_COLORS[index % CHART_COLORS.length] }} /></div>
                        <em>{formatMoney(row.amount, chartCurrency)}</em>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>

            <Card title="Recent transactions" subtitle="Explain every number">
              <div className="recent-list compact">
                {data.transactions.slice(0, 8).map((tx, index) => (
                  <div className="recent-row" key={`${tx.date}-${tx.description}-${index}`}>
                    <div>
                      <strong>{tx.description}</strong>
                      <span>{tx.category ?? 'Uncategorized'} · {tx.date}</span>
                    </div>
                    <em className={tx.amount > 0 ? 'positive' : ''}>{formatMoney(convertAmount(tx.amount, tx.currency, chartCurrency, data.rates), chartCurrency)}</em>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </section>
  );
}
