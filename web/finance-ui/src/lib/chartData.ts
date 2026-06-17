import type { FxRate, SpendingRow } from '../api/types';
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
  if (preference !== 'auto') return preference;
  return dominantCurrency(rows);
}

function rateBetween(rates: FxRate[], from: string, to: string): number | null {
  if (from === to) return 1;
  const direct = rates.find((rate) => rate.from === from && rate.to === to);
  if (direct) return direct.rate;

  const inverse = rates.find((rate) => rate.from === to && rate.to === from);
  if (inverse) return 1 / inverse.rate;

  if (from !== 'UAH' && to !== 'UAH') {
    const fromToUah = rateBetween(rates, from, 'UAH');
    const uahToTarget = rateBetween(rates, 'UAH', to);
    if (fromToUah && uahToTarget) return fromToUah * uahToTarget;
  }

  return null;
}

export function convertAmount(amount: number, from: string, to: string, rates: FxRate[]) {
  const rate = rateBetween(rates, from, to);
  return rate ? amount * rate : amount;
}

export function rowsForCurrency(rows: SpendingRow[], currency = dominantCurrency(rows), rates: FxRate[] = []) {
  if (rates.length === 0) return rows.filter((row) => row.currency === currency);

  const totals = rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.category] = (acc[row.category] ?? 0) + convertAmount(row.amount, row.currency, currency, rates);
    return acc;
  }, {});

  return Object.entries(totals)
    .map(([category, amount]) => ({ category, amount, currency }))
    .sort((a, b) => b.amount - a.amount);
}

export function shortMonth(value: string) {
  const [year, month] = value.split('-');
  if (!year || !month) return value;
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en', { month: 'short' });
}
