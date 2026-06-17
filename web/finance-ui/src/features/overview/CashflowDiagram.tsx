import type { SpendingRow } from '../../api/types';
import { CHART_COLORS } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';

interface CashflowDiagramProps {
  categories: SpendingRow[];
  currency: string;
  income: number;
  expenses: number;
}

const VIEWBOX_WIDTH = 920;
const VIEWBOX_HEIGHT = 320;
const CENTER_X = 430;
const CENTER_Y = 145;
const NODE_WIDTH = 126;
const NODE_HEIGHT = 52;
const MIN_STROKE = 8;
const MAX_STROKE = 34;

function flowWidth(value: number, max: number) {
  if (max <= 0) return MIN_STROKE;
  return MIN_STROKE + (Math.max(value, 0) / max) * (MAX_STROKE - MIN_STROKE);
}

function pathBetween(startX: number, startY: number, endX: number, endY: number) {
  const mid = (startX + endX) / 2;
  return `M ${startX} ${startY} C ${mid} ${startY}, ${mid} ${endY}, ${endX} ${endY}`;
}

export function CashflowDiagram({ categories, currency, income, expenses }: CashflowDiagramProps) {
  const visibleCategories = categories.slice(0, 6);
  const shownExpenses = visibleCategories.reduce((sum, row) => sum + row.amount, 0);
  const otherAmount = Math.max(0, expenses - shownExpenses);
  const categoryNodes = otherAmount > 1 ? [...visibleCategories, { category: 'Other', amount: otherAmount, currency }] : visibleCategories;
  const surplus = Math.max(0, income - expenses);
  const outgoing = surplus > 1 ? [...categoryNodes, { category: 'Surplus', amount: surplus, currency }] : categoryNodes;
  const maxFlow = Math.max(income, expenses, ...outgoing.map((row) => row.amount), 1);
  const sourceValue = income > 0 ? income : expenses;

  if (expenses <= 0 && income <= 0) {
    return <div className="cashflow-empty">No cashflow data yet.</div>;
  }

  return (
    <div className="cashflow-diagram" aria-label="Cashflow diagram">
      <svg viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`} role="img">
        <defs>
          <linearGradient id="cashflowIncome" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#9fe870" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#9fe870" stopOpacity="0.62" />
          </linearGradient>
          <linearGradient id="cashflowSpend" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#10120f" stopOpacity="0.16" />
            <stop offset="100%" stopColor="#10120f" stopOpacity="0.34" />
          </linearGradient>
        </defs>

        <path
          className="cashflow-link income"
          d={pathBetween(150, CENTER_Y, CENTER_X - NODE_WIDTH / 2, CENTER_Y)}
          stroke="url(#cashflowIncome)"
          strokeWidth={flowWidth(sourceValue, maxFlow)}
        />

        {outgoing.map((row, index) => {
          const gap = VIEWBOX_HEIGHT / (outgoing.length + 1);
          const y = gap * (index + 1);
          const isSurplus = row.category === 'Surplus';
          return (
            <g key={row.category}>
              <path
                className="cashflow-link"
                d={pathBetween(CENTER_X + NODE_WIDTH / 2, CENTER_Y, 700, y)}
                stroke={isSurplus ? '#9fe870' : 'url(#cashflowSpend)'}
                strokeOpacity={isSurplus ? 0.55 : 1}
                strokeWidth={flowWidth(row.amount, maxFlow)}
              />
              <g className="cashflow-node target" transform={`translate(700 ${y - NODE_HEIGHT / 2})`}>
                <rect width="170" height={NODE_HEIGHT} rx="18" />
                <circle cx="18" cy="18" r="5" fill={isSurplus ? '#9fe870' : CHART_COLORS[index % CHART_COLORS.length]} />
                <text x="32" y="21" className="node-title">{row.category}</text>
                <text x="32" y="39" className="node-value">{formatCompactMoney(row.amount, currency)}</text>
              </g>
            </g>
          );
        })}

        <g className="cashflow-node source" transform={`translate(24 ${CENTER_Y - NODE_HEIGHT / 2})`}>
          <rect width="126" height={NODE_HEIGHT} rx="18" />
          <text x="16" y="22" className="node-title">Income</text>
          <text x="16" y="40" className="node-value">{formatCompactMoney(sourceValue, currency)}</text>
        </g>

        <g className="cashflow-node center" transform={`translate(${CENTER_X - NODE_WIDTH / 2} ${CENTER_Y - 34})`}>
          <rect width={NODE_WIDTH} height="68" rx="22" />
          <text x="18" y="27" className="node-title">Cashflow</text>
          <text x="18" y="49" className="node-value">{formatMoney(expenses, currency)}</text>
        </g>
      </svg>
    </div>
  );
}
