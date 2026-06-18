export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', title: 'Overview', glyph: 'O' },
  { id: 'accounts', label: 'Accounts', title: 'Accounts', glyph: 'A' },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]['id'];
