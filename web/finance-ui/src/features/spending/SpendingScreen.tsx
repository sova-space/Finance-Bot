import { useEffect, useMemo, useState } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import { apiGet } from '../../api/client';
import type { FxRate, SpendingRow, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, convertAmount, preferredCurrency, rowsForCurrency } from '../../lib/chartData';
import { formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';

interface SpendingData {
  rows: SpendingRow[];
  rates: FxRate[];
  transactions: TransactionItem[];
}

export function SpendingScreen() {
  const { currency } = usePreferences();
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [data, setData] = useState<SpendingData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    async function load() {
      try {
        const [rows, rates, transactions] = await Promise.all([
          apiGet<SpendingRow[]>(`/transactions/spending?period=${period}&exclude_uncategorized=false`),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
        ]);
        if (!cancelled) setData({ rows, rates, transactions });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const chartCurrency = useMemo(() => preferredCurrency(data?.rows ?? [], currency), [currency, data?.rows]);
  const sortedRows = useMemo(
    () => rowsForCurrency(data?.rows ?? [], chartCurrency, data?.rates ?? []),
    [chartCurrency, data?.rates, data?.rows],
  );
  const total = sortedRows.reduce((sum, row) => sum + row.amount, 0);
  const transactions = data?.transactions ?? [];
  const expenses = transactions
    .map((tx) => convertAmount(tx.amount, tx.currency, chartCurrency, data?.rates ?? []))
    .filter((amount) => amount < 0)
    .map(Math.abs);
  const largestExpense = Math.max(0, ...expenses);
  const averageExpense = expenses.length ? expenses.reduce((sum, amount) => sum + amount, 0) / expenses.length : 0;
  const uncategorized = sortedRows.find((row) => row.category === 'Uncategorized');

  return (
    <section className="dashboard-page monarch-page">
      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Reports</p>
          <h2>Spending by category</h2>
        </div>
        <div className="toolbar-row">
          <PeriodSelector value={period} onChange={setPeriod} />
          <button className="soft-button" type="button">By category</button>
          <button className="soft-button" type="button">Change over time</button>
          <button className="soft-button" type="button">Share</button>
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}
      {!data && !error ? <LoadingState /> : null}
      {data ? (
        <div className="analytics-grid monarch-grid">
          <Card className="wide spending-donut-card" title="Spending distribution" subtitle={`${period.replace('_', ' ')} · ${chartCurrency}`}>
            {sortedRows.length === 0 ? (
              <EmptyState>No spending for this period.</EmptyState>
            ) : (
              <div className="donut-report-layout">
                <div className="chart-frame donut-large">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={sortedRows} dataKey="amount" innerRadius="58%" outerRadius="82%" paddingAngle={1} nameKey="category">
                        {sortedRows.map((row, index) => (
                          <Cell key={row.category} fill={row.category === 'Uncategorized' ? '#c7cbc2' : CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatMoney(Number(value), chartCurrency)} contentStyle={{ borderRadius: 18 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-center">
                    <strong>{formatMoney(total, chartCurrency)}</strong>
                    <span>Total</span>
                  </div>
                </div>

                <div className="category-legend-grid">
                  {sortedRows.slice(0, 12).map((row, index) => {
                    const share = total > 0 ? (row.amount / total) * 100 : 0;
                    return (
                      <div className="legend-row rich" key={`${row.category}-${row.currency}`}>
                        <i style={{ background: row.category === 'Uncategorized' ? '#c7cbc2' : CHART_COLORS[index % CHART_COLORS.length] }} />
                        <span>{row.category}</span>
                        <strong>{formatMoney(row.amount, row.currency)}</strong>
                        <em>{share.toFixed(1)}%</em>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </Card>

          <Card className="kpi-card" tone="accent" title="Total spend" subtitle={period.replace('_', ' ')}>
            <strong>{formatMoney(total, chartCurrency)}</strong>
            <span>{sortedRows.length} categories</span>
          </Card>

          <Card className="kpi-card" title="Needs sorting" subtitle="Uncategorized">
            <strong>{uncategorized ? formatMoney(uncategorized.amount, uncategorized.currency) : '0'}</strong>
            <span>{uncategorized ? 'Review transactions' : 'Clean categories'}</span>
          </Card>

          <Card className="wide" title="Transactions" subtitle="Drilldown behind the chart">
            <div className="transaction-mini-table">
              {transactions.slice(0, 10).map((tx, index) => (
                <div className="mini-tx-row" key={`${tx.date}-${tx.description}-${index}`}>
                  <div>
                    <strong>{tx.description}</strong>
                    <span>{tx.date}</span>
                  </div>
                  <span className="category-pill">{tx.category ?? 'Uncategorized'}</span>
                  <em className={tx.amount > 0 ? 'positive' : ''}>{formatMoney(convertAmount(tx.amount, tx.currency, chartCurrency, data.rates), chartCurrency)}</em>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Summary" subtitle="Current view">
            <div className="summary-list">
              <div className="summary-row"><span>Total transactions</span><strong>{transactions.length}</strong></div>
              <div className="summary-row"><span>Largest transaction</span><strong>{formatMoney(largestExpense, chartCurrency)}</strong></div>
              <div className="summary-row"><span>Average transaction</span><strong>{formatMoney(averageExpense, chartCurrency)}</strong></div>
              <div className="summary-row"><span>Total spending</span><strong>{formatMoney(total, chartCurrency)}</strong></div>
            </div>
            <button className="download-button" type="button">Download CSV</button>
          </Card>
        </div>
      ) : null}
    </section>
  );
}
