import { FORMAT_CONFIG } from '../config/format';

export function formatMoney(amount: number, currency: string | undefined = FORMAT_CONFIG.defaultCurrency) {
  try {
    return new Intl.NumberFormat(FORMAT_CONFIG.locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: FORMAT_CONFIG.maximumFractionDigits,
    }).format(amount);
  } catch {
    return `${Math.round(amount)} ${currency}`;
  }
}

export function formatCompactMoney(amount: number, currency: string | undefined = FORMAT_CONFIG.defaultCurrency) {
  try {
    return new Intl.NumberFormat(FORMAT_CONFIG.locale, {
      style: 'currency',
      currency,
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(amount);
  } catch {
    return `${Math.round(amount)} ${currency}`;
  }
}
