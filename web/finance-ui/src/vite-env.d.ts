/// <reference types="vite/client" />

interface TelegramWebApp {
  initData: string;
  ready: () => void;
  expand: () => void;
  HapticFeedback?: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy') => void;
  };
}

interface Window {
  Telegram?: {
    WebApp?: TelegramWebApp;
  };
  FINANCE_API_BASE?: string;
}
