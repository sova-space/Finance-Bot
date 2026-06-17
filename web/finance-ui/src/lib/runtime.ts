export function getApiBase() {
  return window.FINANCE_API_BASE || window.location.origin;
}

export function getBrowserToken() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token') || window.localStorage.getItem('finance_dashboard_token') || '';
  if (params.get('token')) {
    window.localStorage.setItem('finance_dashboard_token', token);
  }
  return token;
}

export function getTelegramInitData() {
  return window.Telegram?.WebApp?.initData ?? '';
}

export function getAuthHeader() {
  const telegramInitData = getTelegramInitData();
  if (telegramInitData) return `tma ${telegramInitData}`;

  const browserToken = getBrowserToken();
  if (browserToken) return `Bearer ${browserToken}`;

  return '';
}

export function initRuntime() {
  const tg = window.Telegram?.WebApp;
  tg?.ready();
  tg?.expand();
}

export function lightFeedback() {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light');
}
