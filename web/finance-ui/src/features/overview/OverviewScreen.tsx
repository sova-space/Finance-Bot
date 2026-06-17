import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { apiGet } from '../../api/client';
import type { Account, MonthlyTrend, SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { DASHBOARD_LIMITS } from '../../config/thresholds';
import { CHART_COLORS, dominantCurrency, rowsForCurrency, shortMonth } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';

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

function currencyPairs(values: Record<string, number>) {
  return Object.entries(values).sort((a, b) => b[1] - a[1]);
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
  const chartCurrency = useMemo(() => dominantCurrency(data?.spending ?? []), [data?.spending]);
  const topCategories = useMemo(
    () => rowsForCurrency([...(data?.spending ?? [])].sort((a, b) => b.amount - a.amount), chartCurrency).slice(0, 7),
    [chartCurrency, data?.spending],
  );
  const trendRows = useMemo(
    () =>
      (data?.trend ?? [])
        .filter((row) => row.currency === chartCurrency)
        .map((row) => ({
          ...row,
          label: shortMonth(row.month),
        })),
    [chartCurrency, data?.trend],
  );
  const totalSpend = topCategories.reduce((sum, row) => sum + row.amount, 0);
  const biggestCategory = topCategories[0];

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page">
      <div className="hero-grid">
        <Card tone="dark" className="hero-card">
          <p className="eyebrow">Net balance</p>
          {currencyPairs(balanceByCurrency).length === 0 ? (
            <EmptyState>No accounts synced yet.</EmptyState>
          ) : (
            <div className="hero-metrics">
              {currencyPairs(balanceByCurrency).map(([currency, amount]) => (
                <div key={currency}>
                  <span>{currency}</span>
                  <strong>{formatMoney(amount, currency)}</strong>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="kpi-card" title="Spent this month" subtitle={chartCurrency}>
          <strong>{formatCompactMoney(spendByCurrency[chartCurrency] ?? 0, chartCurrency)}</strong>
          <span>{biggestCategory ? `${biggestCategory.category} leads spend` : 'No spending yet'}</span>
        </Card>

        <Card className="kpi-card" title="Top category" subtitle="Current month">
          <strong>{biggestCategory?.category ?? '—'}</strong>
          <span>{biggestCategory ? formatMoney(biggestCategory.amount, biggestCategory.currency) : 'No categories yet'}</span>
        </Card>
      </div>

      <div className="analytics-grid">
        <Card className="chart-card wide" title="Cashflow trend" subtitle={`Income vs expenses · ${chartCurrency}`}>
          {trendRows.length === 0 ? (
            <EmptyState>No trend data.</EmptyState>
          ) : (
            <div className="chart-frame tall">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendRows} margin={{ left: 0, right: 8, top: 16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#9fe870" stopOpacity={0.55} />
                      <stop offset="95%" stopColor="#9fe870" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0e0f0c" stopOpacity={0.22} />
                      <stop offset="95%" stopColor="#0e0f0c" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(14,15,12,0.08)" vertical={false} />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#6f726e', fontSize: 12 }} />
                  <YAxis hide />
                  <Tooltip formatter={(value) => formatMoney(Number(value), chartCurrency)} contentStyle={{ borderRadius: 18 }} />
                  <Area type="monotone" dataKey="income" stroke="#4c7f22" strokeWidth={3} fill="url(#incomeFill)" />
                  <Area type="monotone" dataKey="expenses" stroke="#0e0f0c" strokeWidth={3} fill="url(#expenseFill)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
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
                    <div className="pocket-amount">{formatMoney(row.amount, row.currency)}</div>
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
