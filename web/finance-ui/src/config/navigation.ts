export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', title: 'Overview', glyph: 'O' },
  { id: 'accounts', label: 'Accounts', title: 'Accounts', glyph: 'A' },
  { id: 'spending', label: 'Spending', title: 'Spending', glyph: 'S' },
  { id: 'goals', label: 'Goals', title: 'Goals', glyph: 'G' },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]['id'];
