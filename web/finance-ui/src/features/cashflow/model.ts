import type { BudgetRow, FxRate, SpendingRow, TransactionItem } from '../../api/types';
import { convertAmount, rowsForCurrency } from '../../lib/chartData';

export type CashflowJarId = 'living' | 'bills' | 'lifestyle' | 'non_monthly';

export interface CashflowJarDefinition {
  id: CashflowJarId;
  label: string;
  hint: string;
  categories: string[];
}

export interface CashflowCategoryRow extends SpendingRow {
  jarId: CashflowJarId;
  jarLabel: string;
  share: number;
}

export interface CashflowJarRow {
  id: CashflowJarId;
  label: string;
  hint: string;
  currency: string;
  spent: number;
  limit: number;
  remaining: number | null;
  share: number;
  ratio: number | null;
  categoryCount: number;
}

export interface IncomeSourceRow {
  name: string;
  currency: string;
  amount: number;
  count: number;
  share: number;
}

export interface CashflowSummaryModel {
  currency: string;
  income: number;
  spent: number;
  leftAfterSpend: number;
  budgetRemaining: number | null;
  incomeSources: IncomeSourceRow[];
  jars: CashflowJarRow[];
  categories: CashflowCategoryRow[];
  recentTransactions: TransactionItem[];
  needsSorting: number;
}

export const JARS: CashflowJarDefinition[] = [
  {
    id: 'living',
    label: 'Living',
    hint: 'food / groceries / transport / health',
    categories: ['Food & Drink', 'Groceries', 'Transportation', 'Healthcare', 'ATM & Cash'],
  },
  {
    id: 'bills',
    label: 'Bills',
    hint: 'fixed / recurring costs',
    categories: ['Utilities', 'Subscriptions'],
  },
  {
    id: 'lifestyle',
    label: 'Lifestyle',
    hint: 'shopping / fun / learning',
    categories: ['Shopping', 'Entertainment', 'Education', 'Pets'],
  },
  {
    id: 'non_monthly',
    label: 'Non-monthly',
    hint: 'travel / one-offs',
    categories: ['Travel'],
  },
];

const JAR_BY_CATEGORY = new Map<string, CashflowJarDefinition>(
  JARS.flatMap((jar) => jar.categories.map((category) => [category, jar] as const)),
);

const NON_SPEND_CATEGORIES = new Set(['Income', 'Cashback', 'Couple Transfer', 'Partner', 'Finance']);
const NON_INCOME_CATEGORIES = new Set(['Cashback', 'Couple Transfer', 'Partner', 'Finance']);

export function jarForCategory(category: string | null | undefined): CashflowJarDefinition {
  return JAR_BY_CATEGORY.get(category ?? '') ?? JARS[2];
}

export function isTransferLikeDescription(description: string) {
  const normalized = description.toLowerCase();
  return normalized.includes('transfer') || normalized.includes('переказ') || normalized.includes('поповнення');
}

export function isSpendTransaction(tx: TransactionItem) {
  return tx.amount < 0 && !tx.is_pending && !NON_SPEND_CATEGORIES.has(tx.category ?? '') && !isTransferLikeDescription(tx.description);
}

export function isIncomeTransaction(tx: TransactionItem) {
  return tx.amount > 0 && !tx.is_pending && !NON_INCOME_CATEGORIES.has(tx.category ?? '') && !isTransferLikeDescription(tx.description);
}

export function spendingRowsFromTransactions(transactions: TransactionItem[]): SpendingRow[] {
  const totals = new Map<string, SpendingRow>();

  transactions.filter(isSpendTransaction).forEach((tx) => {
    const category = tx.category ?? 'Uncategorized';
    const key = `${category}:${tx.currency}`;
    const existing = totals.get(key) ?? { category, currency: tx.currency, amount: 0 };
    existing.amount += Math.abs(tx.amount);
    totals.set(key, existing);
  });

  return [...totals.values()].sort((a, b) => b.amount - a.amount);
}

function safeConvertAmount(amount: number, from: string, to: string, rates: FxRate[]) {
  if (from !== to && rates.length === 0) return null;
  return convertAmount(amount, from, to, rates);
}

function sumConverted(transactions: TransactionItem[], currency: string, rates: FxRate[], predicate: (tx: TransactionItem) => boolean) {
  return transactions
    .filter(predicate)
    .reduce((sum, tx) => {
      const converted = safeConvertAmount(tx.amount, tx.currency, currency, rates);
      return converted === null ? sum : sum + Math.abs(converted);
    }, 0);
}

function incomeSourcesFromTransactions(transactions: TransactionItem[], currency: string, rates: FxRate[], totalIncome: number): IncomeSourceRow[] {
  const totals = new Map<string, IncomeSourceRow>();
  transactions.filter(isIncomeTransaction).forEach((tx) => {
    const converted = safeConvertAmount(tx.amount, tx.currency, currency, rates);
    if (converted === null) return;
    const name = tx.description || tx.category || 'Income';
    const existing = totals.get(name) ?? { name, currency, amount: 0, count: 0, share: 0 };
    existing.amount += Math.abs(converted);
    existing.count += 1;
    totals.set(name, existing);
  });
  return [...totals.values()]
    .map((row) => ({ ...row, share: totalIncome > 0 ? (row.amount / totalIncome) * 100 : 0 }))
    .sort((a, b) => b.amount - a.amount);
}

export function buildCashflowSummary(
  transactions: TransactionItem[],
  budgets: BudgetRow[],
  rates: FxRate[],
  currency: string,
): CashflowSummaryModel {
  const spendingRows = rowsForCurrency(spendingRowsFromTransactions(transactions), currency, rates);
  const spent = spendingRows.reduce((sum, row) => sum + row.amount, 0);
  const income = sumConverted(transactions, currency, rates, isIncomeTransaction);
  const incomeSources = incomeSourcesFromTransactions(transactions, currency, rates, income);

  const categories: CashflowCategoryRow[] = spendingRows.map((row) => {
    const jar = jarForCategory(row.category);
    return {
      ...row,
      jarId: jar.id,
      jarLabel: jar.label,
      share: spent > 0 ? (row.amount / spent) * 100 : 0,
    };
  });

  const convertedBudgets = budgets
    .map((budget) => {
      const convertedLimit = safeConvertAmount(budget.monthly_limit, budget.currency, currency, rates);
      return convertedLimit === null ? null : { ...budget, monthly_limit: convertedLimit };
    })
    .filter((budget): budget is BudgetRow => budget !== null);

  const jars = JARS.map((jar) => {
    const jarCategories = categories.filter((row) => row.jarId === jar.id);
    const jarSpent = jarCategories.reduce((sum, row) => sum + row.amount, 0);
    const limit = convertedBudgets
      .filter((budget) => jarForCategory(budget.category).id === jar.id)
      .reduce((sum, budget) => sum + budget.monthly_limit, 0);
    const remaining = limit > 0 ? limit - jarSpent : null;
    return {
      id: jar.id,
      label: jar.label,
      hint: jar.hint,
      currency,
      spent: jarSpent,
      limit,
      remaining,
      share: spent > 0 ? (jarSpent / spent) * 100 : 0,
      ratio: limit > 0 ? jarSpent / limit : null,
      categoryCount: jarCategories.length,
    };
  });

  const budgetLimit = jars.reduce((sum, jar) => sum + jar.limit, 0);

  return {
    currency,
    income,
    spent,
    leftAfterSpend: income - spent,
    budgetRemaining: budgetLimit > 0 ? budgetLimit - spent : null,
    incomeSources,
    jars,
    categories,
    recentTransactions: transactions.filter((tx) => isSpendTransaction(tx) || isIncomeTransaction(tx)).slice(0, 12),
    needsSorting: categories.find((row) => row.category === 'Uncategorized')?.amount ?? 0,
  };
}
