export const ANALYTICS_PERIODS = [
  { id: 'this_month', label: 'Month' },
  { id: 'last_90d', label: 'Quarter' },
  { id: 'this_year', label: 'Year' },
] as const;

export type AnalyticsPeriod = (typeof ANALYTICS_PERIODS)[number]['id'];
