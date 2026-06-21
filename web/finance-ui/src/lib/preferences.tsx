import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type Language = 'en' | 'uk';
export type CurrencyPreference = 'auto' | 'UAH' | 'USD' | 'EUR';

const LANGUAGE_STORAGE_KEY = 'finance_web_language';
const CURRENCY_STORAGE_KEY = 'finance_web_currency';

const labels = {
  en: {
    analytics: 'Analytics',
    personalFinance: 'Personal finance',
    liveData: 'Live Monobank data',
    financeBot: 'Finance Bot',
    moneyOs: 'Money OS',
    language: 'Language',
    currency: 'Currency',
    auto: 'Auto',
    navOverview: 'Overview',
    navSpending: 'Income & Expenses',
    navTransactions: 'Transactions',
    navAccounts: 'Accounts',
    navBudget: 'Budget',
    navPlan: 'Plan',
    navGoals: 'Goals',
    titleOverview: 'Overview',
    titleSpending: 'Income & Expenses',
    titleTransactions: 'Transactions',
    titleAccounts: 'Accounts',
    titleBudget: 'Budget control',
    titlePlan: 'Plan ahead',
    titleGoals: 'Goals',
  },
  uk: {
    analytics: 'Аналітика',
    personalFinance: 'Особисті фінанси',
    liveData: 'Дані Monobank наживо',
    financeBot: 'Finance Bot',
    moneyOs: 'Гроші',
    language: 'Мова',
    currency: 'Валюта',
    auto: 'Авто',
    navOverview: 'Огляд',
    navSpending: 'Доходи / Витрати',
    navTransactions: 'Транзакції',
    navAccounts: 'Рахунки',
    navBudget: 'Бюджет',
    navPlan: 'План',
    navGoals: 'Цілі',
    titleOverview: 'Огляд',
    titleSpending: 'Доходи / Витрати',
    titleTransactions: 'Транзакції',
    titleAccounts: 'Рахунки',
    titleBudget: 'Контроль бюджету',
    titlePlan: 'Планування',
    titleGoals: 'Цілі',
  },
} as const;

export type LabelKey = keyof typeof labels.en;

interface PreferencesContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  currency: CurrencyPreference;
  setCurrency: (currency: CurrencyPreference) => void;
  t: (key: LabelKey) => string;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

function initialLanguage(): Language {
  const saved = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (saved === 'en' || saved === 'uk') return saved;
  return navigator.language.toLowerCase().startsWith('uk') ? 'uk' : 'en';
}

function initialCurrency(): CurrencyPreference {
  const saved = window.localStorage.getItem(CURRENCY_STORAGE_KEY);
  if (saved === 'UAH' || saved === 'USD' || saved === 'EUR' || saved === 'auto') return saved;
  return 'auto';
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(initialLanguage);
  const [currency, setCurrencyState] = useState<CurrencyPreference>(initialCurrency);

  const setLanguage = (next: Language) => {
    setLanguageState(next);
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
  };

  const setCurrency = (next: CurrencyPreference) => {
    setCurrencyState(next);
    window.localStorage.setItem(CURRENCY_STORAGE_KEY, next);
  };

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<PreferencesContextValue>(
    () => ({
      language,
      setLanguage,
      currency,
      setCurrency,
      t: (key) => labels[language][key],
    }),
    [currency, language],
  );

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences() {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error('usePreferences must be used inside PreferencesProvider');
  return ctx;
}
