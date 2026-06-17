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
  limit: number;
  spent: number;
  remaining?: number;
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

export interface FxRate {
  from: string;
  to: string;
  rate: number;
  date?: number | null;
}
