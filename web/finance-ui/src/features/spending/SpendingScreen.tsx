import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { apiGet } from '../../api/client';
import type { SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, dominantCurrency, rowsForCurrency } from '../../lib/chartData';
import { formatMoney } from '../../lib/formatMoney';

export function SpendingScreen() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [rows, setRows] = useState<SpendingRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    setError(null);
    async function load() {
      try {
        const data = await apiGet<SpendingRow[]>(`/transactions/spending?period=${period}&exclude_uncategorized=false`);
        if (!cancelled) setRows(data);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const chartCurrency = useMemo(() => dominantCurrency(rows ?? []), [rows]);
  const sortedRows = useMemo(
    () => rowsForCurrency([...(rows ?? [])].sort((a, b) => b.amount - a.amount), chartCurrency),
    [chartCurrency, rows],
  );
  const uncategorized = sortedRows.find((row) => row.category === 'Uncategorized');
  const total = sortedRows.reduce((sum, row) => sum + row.amount, 0);

  return (
    <section className="dashboard-page">
      <div className="section-head">
        <div>
          <p className="eyebrow">Category analytics</p>
          <h2>Where money went</h2>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {error ? <ErrorState message={error} /> : null}
      {!rows && !error ? <LoadingState /> : null}
      {rows ? (
        <div className="analytics-grid">
          <Card className="chart-card wide" title="Spending distribution" subtitle={`Sorted categories · ${chartCurrency}`}>
            {sortedRows.length === 0 ? (
              <EmptyState>No spending for this period.</EmptyState>
            ) : (
              <div className="chart-frame spending-bars">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sortedRows} margin={{ left: 0, right: 16, top: 10, bottom: 12 }}>
                    <CartesianGrid stroke="rgba(14,15,12,0.08)" vertical={false} />
                    <XAxis dataKey="category" axisLine={false} tickLine={false} interval={0} tick={{ fill: '#454745', fontSize: 11 }} />
                    <YAxis hide />
                    <Tooltip formatter={(value) => formatMoney(Number(value), chartCurrency)} contentStyle={{ borderRadius: 18 }} />
                    <Bar dataKey="amount" radius={[999, 999, 0, 0]} barSize={34}>
                      {sortedRows.map((row, index) => (
                        <Cell
                          key={row.category}
                          fill={row.category === 'Uncategorized' ? '#c7cbc2' : CHART_COLORS[index % CHART_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
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

          <Card className="wide" title="Category table" subtitle="Amount and share">
            <div className="data-table">
              {sortedRows.map((row, index) => (
                <div className={row.category === 'Uncategorized' ? 'table-row muted' : 'table-row'} key={`${row.category}-${row.currency}`}>
                  <div className="table-label">
                    <i style={{ background: row.category === 'Uncategorized' ? '#c7cbc2' : CHART_COLORS[index % CHART_COLORS.length] }} />
                    <span>{row.category}</span>
                  </div>
                  <span>{total > 0 ? `${Math.round((row.amount / total) * 100)}%` : '0%'}</span>
                  <strong>{formatMoney(row.amount, row.currency)}</strong>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </section>
  );
}
