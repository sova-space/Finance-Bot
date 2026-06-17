import type { SpendingRow } from '../api/types';
import type { CurrencyPreference } from './preferences';

export const CHART_COLORS = ['#163300', '#4c7f22', '#8bc34a', '#b5ef7d', '#ffd166', '#f4a261', '#2a9d8f'];

export function dominantCurrency(rows: SpendingRow[]) {
  const totals = rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.currency] = (acc[row.currency] ?? 0) + row.amount;
    return acc;
  }, {});

  return Object.entries(totals).sort((a, b) => b[1] - a[1])[0]?.[0] ?? rows[0]?.currency ?? 'UAH';
}

export function preferredCurrency(rows: SpendingRow[], preference: CurrencyPreference) {
  if (preference !== 'auto' && rows.some((row) => row.currency === preference)) return preference;
  return dominantCurrency(rows);
}

export function rowsForCurrency(rows: SpendingRow[], currency = dominantCurrency(rows)) {
  return rows.filter((row) => row.currency === currency);
}

export function shortMonth(value: string) {
  const [year, month] = value.split('-');
  if (!year || !month) return value;
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en', { month: 'short' });
}
