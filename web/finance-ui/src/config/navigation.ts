export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', title: 'Overview', glyph: 'O' },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]['id'];
