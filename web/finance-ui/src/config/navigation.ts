export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', title: 'Overview', glyph: '🧭' },
  { id: 'accounts', label: 'Accounts', title: 'Accounts', glyph: '💰' },
  { id: 'spending', label: 'Income & Expenses', title: 'Income & Expenses', glyph: '📊' },
  { id: 'goals', label: 'Goals', title: 'Goals', glyph: '🎯' },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]['id'];
