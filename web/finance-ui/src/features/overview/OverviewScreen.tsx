import { useEffect, useMemo, useState } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import { apiGet } from '../../api/client';
import type { Account, FxRate, MonthlyTrend, SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { DASHBOARD_LIMITS } from '../../config/thresholds';
import { CHART_COLORS, convertAmount, convertTrendRows, preferredCurrency, rowsForCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { CashflowDiagram } from './CashflowDiagram';

interface OverviewData {
  accounts: Account[];
  rates: FxRate[];
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

export function OverviewScreen() {
  const { currency } = usePreferences();
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [accounts, rates, spending, trend] = await Promise.all([
          apiGet<Account[]>('/accounts'),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<SpendingRow[]>('/transactions/spending?period=this_month&exclude_uncategorized=true'),
          apiGet<MonthlyTrend[]>(`/transactions/trend?months=${DASHBOARD_LIMITS.trendMonths}`),
        ]);
        if (!cancelled) {
          setData({ accounts, rates, spending, trend });
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
  const trendRows = useMemo(
    () => convertTrendRows(data?.trend ?? [], chartCurrency, data?.rates ?? []),
    [chartCurrency, data?.rates, data?.trend],
  );
  const latestTrend = trendRows.at(-1);
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

        <Card className="kpi-card" title="Spent this month" subtitle={`${chartCurrency}${data.rates.length ? ' · converted' : ''}`}>
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
          <CashflowDiagram
            categories={topCategories}
            currency={chartCurrency}
            expenses={currentMonthSpend}
            income={latestTrend?.income ?? currentMonthSpend}
          />
        </Card>

        <Card className="chart-card" title="Spend mix" subtitle={`Top categories · ${chartCurrency}`}>
          {topCategories.length === 0 ? (
            <EmptyState>No categories yet.</EmptyState>
          ) : (
            <div className="donut-layout">
              <div className="chart-frame donut">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={topCategories} dataKey="amount" nameKey="category" innerRadius="62%" outerRadius="88%" paddingAngle={2}>
                      {topCategories.map((row, index) => (
                        <Cell key={row.category} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatMoney(Number(value), chartCurrency)} contentStyle={{ borderRadius: 18 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-center">
                  <span>Total</span>
                  <strong>{formatMoney(totalSpend, chartCurrency)}</strong>
                </div>
              </div>
              <div className="legend-list">
                {topCategories.slice(0, 5).map((row, index) => (
                  <div className="legend-row" key={row.category}>
                    <i style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                    <span>{row.category}</span>
                    <strong>{formatMoney(row.amount, row.currency)}</strong>
                  </div>
                ))}
              </div>
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
