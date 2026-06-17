export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', title: 'Overview', glyph: 'O' },
  { id: 'cashflow', label: 'Cash Flow', title: 'Cash flow', glyph: 'C' },
  { id: 'spending', label: 'Spending', title: 'Spending analytics', glyph: 'S' },
  { id: 'transactions', label: 'Transactions', title: 'Transactions', glyph: 'T' },
  { id: 'accounts', label: 'Accounts', title: 'Accounts', glyph: 'A' },
  { id: 'budget', label: 'Budget', title: 'Budget control', glyph: 'B' },
  { id: 'plan', label: 'Plan', title: 'Plan ahead', glyph: 'P' },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]['id'];
