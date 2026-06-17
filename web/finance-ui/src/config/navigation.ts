export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'spending', label: 'Spending', icon: '💸' },
  { id: 'budget', label: 'Budget', icon: '🧺' },
  { id: 'plan', label: 'Plan', icon: '🎯' },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]['id'];
