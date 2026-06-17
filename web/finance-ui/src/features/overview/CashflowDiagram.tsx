import { useMemo } from 'react';
import { sankey, sankeyJustify, sankeyLinkHorizontal } from 'd3-sankey';

import type { SpendingRow } from '../../api/types';
import { CHART_COLORS } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';

interface CashflowDiagramProps {
  categories: SpendingRow[];
  currency: string;
  expenses: number;
}

interface CashflowNode {
  name: string;
  value: number;
  color: string;
  kind: 'source' | 'category';
}

type CashflowLink = { source: number; target: number; value: number; color: string };

const WIDTH = 980;
const HEIGHT = 260;
const NODE_WIDTH = 12;

function buildData(categories: SpendingRow[], expenses: number) {
  const visible = categories.slice(0, 6);
  const shown = visible.reduce((sum, row) => sum + row.amount, 0);
  const other = Math.max(0, expenses - shown);
  const spendingNodes = other > 1 ? [...visible, { category: 'Other', amount: other, currency: visible[0]?.currency ?? 'UAH' }] : visible;

  const nodes: CashflowNode[] = [
    { name: 'Spending', value: expenses, color: '#26a269', kind: 'source' },
    ...spendingNodes.map((row, index) => ({
      name: row.category,
      value: row.amount,
      color: CHART_COLORS[index % CHART_COLORS.length],
      kind: 'category' as const,
    })),
  ];

  const links: CashflowLink[] = spendingNodes.map((row, index) => ({
    source: 0,
    target: index + 1,
    value: row.amount,
    color: CHART_COLORS[index % CHART_COLORS.length],
  }));

  return { nodes, links };
}

export function CashflowDiagram({ categories, currency, expenses }: CashflowDiagramProps) {
  const graph = useMemo(() => {
    const data = buildData(categories, expenses);
    return sankey<CashflowNode, CashflowLink>()
      .nodeWidth(NODE_WIDTH)
      .nodePadding(14)
      .nodeAlign(sankeyJustify)
      .extent([[18, 16], [WIDTH - 18, HEIGHT - 16]])({
        nodes: data.nodes.map((node) => ({ ...node })),
        links: data.links.map((link) => ({ ...link })),
      });
  }, [categories, expenses]);

  if (expenses <= 0) {
    return <div className="cashflow-empty">No spending data yet.</div>;
  }

  const path = sankeyLinkHorizontal<CashflowNode, CashflowLink>();

  return (
    <div className="cashflow-diagram d3-cashflow" aria-label="Spending flow diagram">
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
                strokeOpacity={0.28}
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
            const labelLeft = node.kind === 'category';
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
