import { FORMAT_CONFIG } from '../config/format';

function currentLocale() {
  try {
    return window.localStorage.getItem('finance_web_language') === 'en' ? 'en-US' : FORMAT_CONFIG.locale;
  } catch {
    return FORMAT_CONFIG.locale;
  }
}

export function formatMoney(amount: number, currency: string | undefined = FORMAT_CONFIG.defaultCurrency) {
  try {
    return new Intl.NumberFormat(currentLocale(), {
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
    return new Intl.NumberFormat(currentLocale(), {
      style: 'currency',
      currency,
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(amount);
  } catch {
    return `${Math.round(amount)} ${currency}`;
  }
}
