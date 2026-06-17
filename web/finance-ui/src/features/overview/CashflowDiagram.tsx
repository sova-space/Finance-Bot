import { useMemo } from 'react';
import { sankey, sankeyCenter, sankeyLinkHorizontal } from 'd3-sankey';

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
  color: string;
  kind: 'income' | 'cashflow' | 'category' | 'surplus';
}

type CashflowLink = { source: number; target: number; value: number; color: string };

const WIDTH = 980;
const HEIGHT = 300;
const NODE_WIDTH = 12;

function buildData(categories: SpendingRow[], income: number, expenses: number) {
  const visible = categories.slice(0, 5);
  const shown = visible.reduce((sum, row) => sum + row.amount, 0);
  const other = Math.max(0, expenses - shown);
  const spendingNodes = other > 1 ? [...visible, { category: 'Other', amount: other, currency: visible[0]?.currency ?? 'UAH' }] : visible;
  const surplus = Math.max(0, income - expenses);
  const source = Math.max(income, expenses);

  const nodes: CashflowNode[] = [
    { name: 'Income', value: source, color: '#14a3b8', kind: 'income' },
    { name: 'Cashflow', value: expenses, color: '#26a269', kind: 'cashflow' },
    ...spendingNodes.map((row, index) => ({
      name: row.category,
      value: row.amount,
      color: CHART_COLORS[index % CHART_COLORS.length],
      kind: 'category' as const,
    })),
  ];

  if (surplus > 1) {
    nodes.push({ name: 'Saved', value: surplus, color: '#9fe870', kind: 'surplus' });
  }

  const links: CashflowLink[] = [
    { source: 0, target: 1, value: source, color: '#14a3b8' },
    ...spendingNodes.map((row, index) => ({
      source: 1,
      target: index + 2,
      value: row.amount,
      color: CHART_COLORS[index % CHART_COLORS.length],
    })),
    ...(surplus > 1 ? [{ source: 1, target: nodes.length - 1, value: surplus, color: '#9fe870' }] : []),
  ];

  return { nodes, links };
}

export function CashflowDiagram({ categories, currency, income, expenses }: CashflowDiagramProps) {
  const graph = useMemo(() => {
    const data = buildData(categories, income, expenses);
    return sankey<CashflowNode, CashflowLink>()
      .nodeWidth(NODE_WIDTH)
      .nodePadding(18)
      .nodeAlign(sankeyCenter)
      .extent([[18, 18], [WIDTH - 18, HEIGHT - 18]])({
        nodes: data.nodes.map((node) => ({ ...node })),
        links: data.links.map((link) => ({ ...link })),
      });
  }, [categories, expenses, income]);

  if (expenses <= 0 && income <= 0) {
    return <div className="cashflow-empty">No cashflow data yet.</div>;
  }

  const path = sankeyLinkHorizontal<CashflowNode, CashflowLink>();

  return (
    <div className="cashflow-diagram d3-cashflow" aria-label="Cashflow diagram">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img">
        <g className="d3-cashflow-links">
          {graph.links.map((link, index) => {
            const source = link.source as unknown as CashflowNode;
            const target = link.target as unknown as CashflowNode;
            return (
              <path
                d={path(link) ?? undefined}
                key={index}
                stroke={link.color}
                strokeOpacity={target.kind === 'surplus' ? 0.5 : 0.24}
                strokeWidth={Math.max(2, link.width ?? 1)}
              >
                <title>{`${source.name} → ${target.name}: ${formatMoney(link.value, currency)}`}</title>
              </path>
            );
          })}
        </g>

        <g className="d3-cashflow-nodes">
          {graph.nodes.map((node) => {
            const x0 = node.x0 ?? 0;
            const x1 = node.x1 ?? x0 + NODE_WIDTH;
            const y0 = node.y0 ?? 0;
            const y1 = node.y1 ?? y0 + 4;
            const labelLeft = x0 > WIDTH * 0.65;
            const labelX = labelLeft ? x0 - 10 : x1 + 10;
            const y = (y0 + y1) / 2;
            return (
              <g key={node.name}>
                <rect
                  fill={node.color}
                  height={Math.max(4, y1 - y0)}
                  rx={6}
                  width={Math.max(4, x1 - x0)}
                  x={x0}
                  y={y0}
                />
                <text className="d3-node-title" textAnchor={labelLeft ? 'end' : 'start'} x={labelX} y={y - 3}>
                  {node.name}
                </text>
                <text className="d3-node-value" textAnchor={labelLeft ? 'end' : 'start'} x={labelX} y={y + 13}>
                  {formatCompactMoney(node.value, currency)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
