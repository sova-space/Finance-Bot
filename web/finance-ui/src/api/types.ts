export interface Account {
  account_id: string;
  name: string;
  currency: string;
  balance: number;
  spent?: number;
  type: string;
  is_fop: boolean;
  synced_at: string | null;
}

export interface ManualBalance {
  id: string;
  kind: 'cash' | 'asset' | 'debt';
  name: string;
  currency: string;
  amount: number;
  ownership_percent: number;
  note?: string | null;
  updated_at?: string | null;
}

export interface IncomeTotal {
  currency: string;
  amount: number;
}

export interface AccountsSummary {
  bank_accounts: Account[];
  manual_balances: ManualBalance[];
  earnings: {
    month: IncomeTotal[];
    year: IncomeTotal[];
  };
}

export interface SpendingRow {
  category: string;
  currency: string;
  amount: number;
}

export interface MonthlyTrend {
  month: string;
  currency: string;
  income: number;
  expenses: number;
}

export interface BudgetRow {
  category: string;
  currency: string;
  monthly_limit: number;
  spent: number;
  remaining?: number;
  exceeded?: boolean;
}

export interface Pocket {
  id: string;
  category: string;
  emoji?: string | null;
  currency: string;
  balance: number;
  monthly_budget: number;
}

export interface Goal {
  id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  currency: string;
  deadline?: string | null;
}

export interface ForecastRow {
  date?: string;
  label?: string;
  amount?: number;
  currency?: string;
  balance?: number;
}

export interface TransactionItem {
  date: string;
  description: string;
  amount: number;
  currency: string;
  category?: string | null;
  mode?: string | null;
  is_pending?: boolean;
}

export interface FxRate {
  from: string;
  to: string;
  rate: number;
  date?: number | null;
}
