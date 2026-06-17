export const ANALYTICS_PERIODS = [
  { id: 'this_month', label: 'This month' },
  { id: 'last_month', label: 'Last month' },
  { id: 'last_7d', label: '7d' },
  { id: 'last_30d', label: '30d' },
  { id: 'last_90d', label: '90d' },
] as const;

export type AnalyticsPeriod = (typeof ANALYTICS_PERIODS)[number]['id'];
