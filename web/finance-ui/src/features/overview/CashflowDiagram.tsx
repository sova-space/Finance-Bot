import { useMemo } from 'react';
import { ArcElement, Chart as ChartJS, Legend, Tooltip } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

import type { SpendingRow } from '../../api/types';
import { CHART_COLORS } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';

ChartJS.register(ArcElement, Tooltip, Legend);

interface CashflowDiagramProps {
  categories: SpendingRow[];
  currency: string;
  expenses: number;
}

export function CashflowDiagram({ categories, currency, expenses }: CashflowDiagramProps) {
  const rows = useMemo(() => categories.slice(0, 6), [categories]);
  const chartData = useMemo(
    () => ({
      labels: rows.map((row) => row.category),
      datasets: [
        {
          data: rows.map((row) => row.amount),
          backgroundColor: rows.map((_, index) => CHART_COLORS[index % CHART_COLORS.length]),
          borderColor: '#f7f6ef',
          borderRadius: 8,
          borderWidth: 4,
          hoverOffset: 4,
          spacing: 2,
        },
      ],
    }),
    [rows],
  );

  if (expenses <= 0 || rows.length === 0) {
    return <div className="cashflow-empty">No spending data yet.</div>;
  }

  return (
    <div className="cashflow-donut-layout" aria-label="Spending by category chart">
      <div className="cashflow-donut-wrap">
        <Doughnut
          data={chartData}
          options={{
            cutout: '72%',
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (context) => `${context.label}: ${formatMoney(Number(context.raw), currency)}`,
                },
              },
            },
          }}
        />
        <div className="cashflow-donut-center">
          <span>Spent</span>
          <strong>{formatCompactMoney(expenses, currency)}</strong>
        </div>
      </div>

      <div className="cashflow-breakdown-list">
        {rows.map((row, index) => {
          const share = expenses > 0 ? Math.round((row.amount / expenses) * 100) : 0;
          return (
            <div className="cashflow-breakdown-row" key={row.category}>
              <span className="cashflow-color" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
              <strong>{row.category}</strong>
              <em>{formatCompactMoney(row.amount, row.currency)}</em>
              <small>{share}%</small>
            </div>
          );
        })}
      </div>
    </div>
  );
}
