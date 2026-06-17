import { useMemo } from 'react';
import { Sankey, Tooltip } from 'recharts';
import type { SankeyLinkProps, SankeyNodeProps } from 'recharts';

import type { SpendingRow } from '../../api/types';
import { CHART_COLORS } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';

interface CashflowDiagramProps {
  categories: SpendingRow[];
  currency: string;
  income: number;
  expenses: number;
}

interface CashflowNode {
  name: string;
  value: number;
  formattedValue: string;
  color: string;
  kind: 'source' | 'center' | 'category' | 'surplus';
}

const NODE_WIDTH = 18;
const CHART_HEIGHT = 320;

function buildSankeyData(categories: SpendingRow[], currency: string, income: number, expenses: number) {
  const visibleCategories = categories.slice(0, 7);
  const shownExpenses = visibleCategories.reduce((sum, row) => sum + row.amount, 0);
  const otherAmount = Math.max(0, expenses - shownExpenses);
  const categoryNodes = otherAmount > 1 ? [...visibleCategories, { category: 'Other', amount: otherAmount, currency }] : visibleCategories;
  const surplus = Math.max(0, income - expenses);
  const sourceValue = Math.max(income, expenses);

  const nodes: CashflowNode[] = [
    { name: 'Income', value: sourceValue, formattedValue: formatCompactMoney(sourceValue, currency), color: '#16a6b6', kind: 'source' },
    { name: 'Cashflow', value: expenses, formattedValue: formatCompactMoney(expenses, currency), color: '#2f8f46', kind: 'center' },
    ...categoryNodes.map((row, index) => ({
      name: row.category,
      value: row.amount,
      formattedValue: formatCompactMoney(row.amount, currency),
      color: CHART_COLORS[index % CHART_COLORS.length],
      kind: 'category' as const,
    })),
  ];

  if (surplus > 1) {
    nodes.push({ name: 'Surplus', value: surplus, formattedValue: formatCompactMoney(surplus, currency), color: '#9fe870', kind: 'surplus' });
  }

  return {
    nodes,
    links: [
      { source: 0, target: 1, value: sourceValue },
      ...categoryNodes.map((row, index) => ({ source: 1, target: index + 2, value: row.amount })),
      ...(surplus > 1 ? [{ source: 1, target: nodes.length - 1, value: surplus }] : []),
    ],
  };
}

function CashflowNodeShape({ height, payload, width, x, y }: SankeyNodeProps) {
  const node = payload as unknown as CashflowNode;
  const isCenter = node.kind === 'center';
  const labelX = x + width + 8;
  const isRightSide = x > 520;
  const textAnchor = isRightSide ? 'end' : 'start';
  const resolvedLabelX = isRightSide ? x - 8 : labelX;

  return (
    <g className={`recharts-cashflow-node ${node.kind}`}>
      <rect
        fill={node.color}
        fillOpacity={isCenter ? 0.95 : 0.82}
        height={height}
        rx={9}
        width={width}
        x={x}
        y={y}
      />
      <text className="sankey-node-title" textAnchor={textAnchor} x={resolvedLabelX} y={y + Math.max(14, height / 2 - 4)}>
        {node.name}
      </text>
      <text className="sankey-node-value" textAnchor={textAnchor} x={resolvedLabelX} y={y + Math.max(30, height / 2 + 13)}>
        {node.formattedValue}
      </text>
    </g>
  );
}

function CashflowLinkShape(props: SankeyLinkProps) {
  const { linkWidth, payload, sourceControlX, sourceX, sourceY, targetControlX, targetX, targetY } = props;
  const target = payload.target as unknown as CashflowNode;
  const d = `M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`;
  return <path className="recharts-cashflow-link" d={d} stroke={target.color} strokeOpacity={target.kind === 'surplus' ? 0.48 : 0.26} strokeWidth={Math.max(3, linkWidth)} />;
}

export function CashflowDiagram({ categories, currency, income, expenses }: CashflowDiagramProps) {
  const data = useMemo(() => buildSankeyData(categories, currency, income, expenses), [categories, currency, expenses, income]);

  if (expenses <= 0 && income <= 0) {
    return <div className="cashflow-empty">No cashflow data yet.</div>;
  }

  return (
    <div className="cashflow-diagram recharts-sankey" aria-label="Cashflow Sankey chart">
      <Sankey
        data={data}
        height={CHART_HEIGHT}
        iterations={48}
        link={CashflowLinkShape}
        margin={{ top: 10, right: 138, bottom: 10, left: 88 }}
        node={CashflowNodeShape}
        nodePadding={18}
        nodeWidth={NODE_WIDTH}
        sort={false}
        verticalAlign="justify"
        width="100%"
      >
        <Tooltip
          contentStyle={{ border: '1px solid rgba(14,15,12,0.1)', borderRadius: 18, boxShadow: '0 16px 42px rgba(14,15,12,0.12)' }}
          formatter={(value) => formatMoney(Number(value), currency)}
        />
      </Sankey>
    </div>
  );
}
