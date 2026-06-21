import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState } from 'react';

import { apiGet, apiPatch, apiPost } from '../../api/client';
import type { BudgetRow, FxRate, MonthlyTrend, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { CHART_COLORS, convertAmount, preferredCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';
import { buildCashflowSummary, isIncomeTransaction, isSpendTransaction, jarForCategory, spendingRowsFromTransactions, type CashflowJarId } from './model';

interface CashflowData {
  budgets: BudgetRow[];
  categories: string[];
  rates: FxRate[];
  transactions: TransactionItem[];
  trend: MonthlyTrend[];
}

function ratioTone(ratio: number | null) {
  if (ratio === null) return 'default';
  if (ratio >= 1) return 'danger';
  if (ratio >= 0.8) return 'warning';
  return 'default';
}

function periodLabel(period: AnalyticsPeriod) {
  if (period === 'this_year') return 'year';
  if (period === 'last_90d') return 'quarter';
  return 'month';
}

export function CashflowScreen() {
  const { currency } = usePreferences();
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [selectedJar, setSelectedJar] = useState<CashflowJarId | 'all'>('all');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [data, setData] = useState<CashflowData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortDrafts, setSortDrafts] = useState<Record<string, string>>({});
  const [sortStatus, setSortStatus] = useState<Record<string, 'saving' | 'saved' | 'error'>>({});
  const [budgetDrafts, setBudgetDrafts] = useState<Record<string, string>>({});
  const [budgetSaveStatus, setBudgetSaveStatus] = useState<Record<string, 'saving' | 'saved' | 'error'>>({});

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    async function load() {
      try {
        const [transactions, budgets, rates, trend, categories] = await Promise.all([
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
          apiGet<BudgetRow[]>('/budgets').catch(() => []),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<MonthlyTrend[]>('/transactions/trend?months=12').catch(() => []),
          apiGet<string[]>('/transactions/categories').catch(() => []),
        ]);
        if (!cancelled) setData({ transactions, budgets, categories, rates, trend });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const spendingRows = useMemo(() => spendingRowsFromTransactions(data?.transactions ?? []), [data?.transactions]);
  const chartCurrency = useMemo(() => preferredCurrency(spendingRows, currency), [currency, spendingRows]);
  const summary = useMemo(
    () => buildCashflowSummary(data?.transactions ?? [], data?.budgets ?? [], data?.rates ?? [], chartCurrency),
    [chartCurrency, data?.budgets, data?.rates, data?.transactions],
  );
  const visibleCategories = selectedJar === 'all' ? summary.categories : summary.categories.filter((row) => row.jarId === selectedJar);
  const activeCategory = selectedCategory && visibleCategories.some((row) => row.category === selectedCategory) ? selectedCategory : visibleCategories[0]?.category ?? null;
  const incomeTransactions = (data?.transactions ?? []).filter(isIncomeTransaction);
  const spendTransactions = (data?.transactions ?? []).filter(isSpendTransaction);
  const categoryTransactions = activeCategory
    ? spendTransactions.filter((tx) => (tx.category ?? 'Uncategorized') === activeCategory)
    : [];
  const visibleTransactions = categoryTransactions.length > 0
    ? categoryTransactions
    : summary.recentTransactions.filter((tx) => selectedJar === 'all' || jarForCategory(tx.category).id === selectedJar);
  const monthlyTrend = useMemo(
    () => (data?.trend ?? []).map((row) => ({
      ...row,
      income: convertAmount(row.income, row.currency, chartCurrency, data?.rates ?? []),
      expenses: convertAmount(row.expenses, row.currency, chartCurrency, data?.rates ?? []),
      left: convertAmount(row.income - row.expenses, row.currency, chartCurrency, data?.rates ?? []),
      currency: chartCurrency,
    })),
    [chartCurrency, data?.rates, data?.trend],
  );
  const uncategorizedTransactions = (data?.transactions ?? []).filter((tx) => tx.id && tx.amount < 0 && !tx.is_pending && !tx.category);
  const categoryOptions = data?.categories ?? [];
  const categoryBudgetRows = useMemo(() => {
    const canonicalCategories = new Set(categoryOptions);
    const budgetMap = new Map((data?.budgets ?? []).map((budget) => [budget.category, budget]));
    const byCategory = new Map<string, { category: string; spent: number; budget?: BudgetRow }>();
    if (period === 'this_month') {
      summary.categories.forEach((row) => {
        if (!canonicalCategories.has(row.category)) return;
        byCategory.set(row.category, { category: row.category, spent: row.amount, budget: budgetMap.get(row.category) });
      });
    }
    (data?.budgets ?? []).forEach((budget) => {
      const budgetSpent = convertAmount(budget.spent, budget.currency, chartCurrency, data?.rates ?? []);
      byCategory.set(budget.category, { category: budget.category, spent: budgetSpent, budget });
    });
    return [...byCategory.values()].sort((a, b) => {
      const aHasBudget = a.budget ? 1 : 0;
      const bHasBudget = b.budget ? 1 : 0;
      return bHasBudget - aHasBudget || b.spent - a.spent || a.category.localeCompare(b.category);
    });
  }, [categoryOptions, chartCurrency, data?.budgets, data?.rates, period, summary.categories]);
  const budgetEditorTotals = categoryBudgetRows.reduce(
    (totals, row) => {
      const limit = row.budget ? convertAmount(row.budget.monthly_limit, row.budget.currency, chartCurrency, data?.rates ?? []) : 0;
      return { limit: totals.limit + limit, spent: totals.spent + row.spent };
    },
    { limit: 0, spent: 0 },
  );
  const budgetEditorStatus = budgetEditorTotals.limit > 0
    ? budgetEditorTotals.limit - budgetEditorTotals.spent
    : null;

  async function saveBudget(category: string, fallbackLimit: number | null) {
    const rawAmount = budgetDrafts[category] ?? (fallbackLimit === null ? '' : String(fallbackLimit));
    const amount = Number(rawAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setBudgetSaveStatus((current) => ({ ...current, [category]: 'error' }));
      return;
    }
    setBudgetSaveStatus((current) => ({ ...current, [category]: 'saving' }));
    try {
      await apiPost('/budgets', { category, monthly_limit: amount, currency: chartCurrency });
      const budgets = await apiGet<BudgetRow[]>('/budgets');
      setData((current) => (current ? { ...current, budgets } : current));
      setBudgetDrafts((current) => ({ ...current, [category]: String(amount) }));
      setBudgetSaveStatus((current) => ({ ...current, [category]: 'saved' }));
      window.setTimeout(() => setBudgetSaveStatus((current) => {
        const next = { ...current };
        delete next[category];
        return next;
      }), 1000);
    } catch {
      setBudgetSaveStatus((current) => ({ ...current, [category]: 'error' }));
    }
  }

  async function labelTransaction(tx: TransactionItem) {
    if (!tx.id) return;
    const category = sortDrafts[tx.id];
    if (!category) return;
    setSortStatus((current) => ({ ...current, [tx.id as string]: 'saving' }));
    try {
      const updated = await apiPatch<TransactionItem>(`/transactions/${tx.id}/label`, { category });
      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          transactions: current.transactions.map((row) => (row.id === tx.id ? { ...row, ...updated } : row)),
        };
      });
      setSortStatus((current) => ({ ...current, [tx.id as string]: 'saved' }));
      window.setTimeout(() => setSortStatus((current) => {
        const next = { ...current };
        delete next[tx.id as string];
        return next;
      }), 1000);
    } catch {
      setSortStatus((current) => ({ ...current, [tx.id as string]: 'error' }));
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page cashflow-page">
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow="finance"
          title="Income & Expenses"
          description={`Income transactions, expense categories · ${periodLabel(period)} · ${chartCurrency}`}
          meta={<SovaBadge tone={summary.leftAfterSpend >= 0 ? 'good' : 'bad'}>{summary.leftAfterSpend >= 0 ? 'within income' : 'over income'}</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: 'Income', value: formatCompactMoney(summary.income, chartCurrency), hint: `${summary.incomeSources.length} sources`, tone: 'good' },
            { label: 'Expenses', value: formatCompactMoney(summary.spent, chartCurrency), hint: `${summary.categories.length} categories`, tone: 'warn' },
            { label: 'Left', value: formatCompactMoney(summary.leftAfterSpend, chartCurrency), hint: 'income - expenses', tone: summary.leftAfterSpend >= 0 ? 'accent' : 'warn' },
            { label: 'Needs sorting', value: summary.needsSorting ? formatCompactMoney(summary.needsSorting, chartCurrency) : '0', hint: 'uncategorized', tone: summary.needsSorting ? 'neutral' : 'good' },
          ]}
        />
      </div>

      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Range</p>
          <h2>Income and expenses</h2>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      <div className="cashflow-report-grid">
        <Card className="wide" title="Needs sorting" subtitle="Label uncategorized spending and teach future rules">
          {uncategorizedTransactions.length === 0 ? (
            <EmptyState>All visible spending is categorized. New unsorted expenses will appear here.</EmptyState>
          ) : (
            <div className="sorting-list">
              {uncategorizedTransactions.slice(0, 8).map((tx) => {
                const txId = tx.id as string;
                const status = sortStatus[txId];
                return (
                  <div className="sorting-row" key={txId}>
                    <div>
                      <strong>{tx.description}</strong>
                      <span>{tx.date} · {formatMoney(tx.amount, tx.currency)}</span>
                    </div>
                    <select
                      onChange={(event) => setSortDrafts((current) => ({ ...current, [txId]: event.target.value }))}
                      value={sortDrafts[txId] ?? ''}
                    >
                      <option value="">Category</option>
                      {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
                    </select>
                    <button disabled={!sortDrafts[txId] || status === 'saving'} onClick={() => labelTransaction(tx)} type="button">
                      {status === 'saving' ? 'Saving' : status === 'saved' ? 'Saved' : 'Label'}
                    </button>
                    {status === 'error' ? <small className="danger-text">error</small> : null}
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="wide" title="Monthly income" subtitle="Income and expenses by month">
          {monthlyTrend.length === 0 ? (
            <EmptyState>No monthly data yet.</EmptyState>
          ) : (
            <div className="chart-frame income-expense-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyTrend.slice(-12)} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(14,15,12,0.08)" vertical={false} />
                  <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#6b7067', fontWeight: 800 }} />
                  <YAxis tickFormatter={(value) => formatCompactMoney(Number(value), chartCurrency)} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#6b7067', fontWeight: 800 }} width={54} />
                  <Tooltip formatter={(value, name) => [formatMoney(Number(value), chartCurrency), name === 'income' ? 'Income' : name === 'expenses' ? 'Expenses' : 'Left']} contentStyle={{ borderRadius: 18 }} />
                  <Bar dataKey="income" fill="#16a34a" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="expenses" fill="#f97316" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="wide" title="Income transactions" subtitle="Actual money received in this range">
          {incomeTransactions.length === 0 ? (
            <EmptyState>No income transactions for this range.</EmptyState>
          ) : (
            <div className="transaction-mini-table income-transaction-list">
              {incomeTransactions.slice(0, 12).map((tx, index) => (
                <div className="mini-tx-row" key={`${tx.id ?? tx.date}-${tx.description}-${index}`}>
                  <div>
                    <strong>{tx.description}</strong>
                    <span>{tx.category ?? 'Income'} · {tx.date}</span>
                  </div>
                  <span className="category-pill income">Income</span>
                  <em className="positive">{formatMoney(tx.amount, tx.currency)}</em>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="wide" title="Income sources" subtitle="Where money came from">
          {summary.incomeSources.length === 0 ? (
            <EmptyState>No income for this range.</EmptyState>
          ) : (
            <div className="cashflow-category-list">
              {summary.incomeSources.slice(0, 8).map((row, index) => (
                <div className="cashflow-category-row" key={row.name}>
                  <span className="cashflow-color income" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <div>
                    <strong>{row.name}</strong>
                    <small>{row.count} transactions</small>
                  </div>
                  <em>{formatMoney(row.amount, row.currency)}</em>
                  <small>{Math.round(row.share)}%</small>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="wide" title="Spending groups" subtitle="Normal groups, not budget rules">
          <div className="spending-group-grid">
            {summary.jars.map((jar, index) => {
              const active = selectedJar === jar.id;
              return (
                <button className={`spending-group-card ${active ? 'active' : ''}`} key={jar.id} onClick={() => setSelectedJar(active ? 'all' : jar.id)} type="button">
                  <span className="jar-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                  <strong>{jar.label}</strong>
                  <em>{formatCompactMoney(jar.spent, chartCurrency)}</em>
                  <small>{jar.hint} · {Math.round(jar.share)}%</small>
                </button>
              );
            })}
          </div>
          <button className="soft-button cashflow-clear" onClick={() => setSelectedJar('all')} type="button">All groups</button>
        </Card>

        <Card className="wide" title="Expense categories" subtitle="Pick a category to see its transactions">
          {visibleCategories.length === 0 ? (
            <EmptyState>No spending for this range.</EmptyState>
          ) : (
            <div className="cashflow-category-list category-picker-list">
              {visibleCategories.map((row, index) => {
                const active = activeCategory === row.category;
                const count = spendTransactions.filter((tx) => (tx.category ?? 'Uncategorized') === row.category).length;
                return (
                  <button className={`cashflow-category-row category-picker-row ${active ? 'active' : ''}`} key={`${row.category}-${row.currency}`} onClick={() => setSelectedCategory(row.category)} type="button">
                    <span className="cashflow-color" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                    <div>
                      <strong>{row.category}</strong>
                      <small>{row.jarLabel} · {count} tx</small>
                    </div>
                    <em>{formatMoney(row.amount, row.currency)}</em>
                    <small>{Math.round(row.share)}%</small>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <Card title="Category transactions" subtitle={activeCategory ?? 'recent, cleaned'}>
          {visibleTransactions.length === 0 ? (
            <EmptyState>No transactions.</EmptyState>
          ) : (
            <div className="transaction-mini-table">
              {visibleTransactions.slice(0, 10).map((tx, index) => (
                <div className="mini-tx-row" key={`${tx.date}-${tx.description}-${index}`}>
                  <div>
                    <strong>{tx.description}</strong>
                    <span>{tx.category ?? 'Uncategorized'} · {tx.date}</span>
                  </div>
                  <span className="category-pill">{tx.amount > 0 ? 'Income' : jarForCategory(tx.category).label}</span>
                  <em className={tx.amount > 0 ? 'positive' : ''}>{formatMoney(tx.amount, tx.currency)}</em>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="wide" title="Budget editor" subtitle="monthly limits · current-month pressure">
          <div className="budget-editor-list">
            {categoryBudgetRows.length === 0 ? <EmptyState>No spending categories yet.</EmptyState> : null}
            {categoryBudgetRows.slice(0, 12).map((row) => {
              const limit = row.budget?.monthly_limit ?? null;
              const draft = budgetDrafts[row.category] ?? (limit === null ? '' : String(limit));
              const status = budgetSaveStatus[row.category];
              const convertedLimit = limit === null ? null : convertAmount(limit, row.budget?.currency ?? chartCurrency, chartCurrency, data.rates);
              const remaining = convertedLimit === null ? null : convertedLimit - row.spent;
              return (
                <div className="budget-editor-row" key={row.category}>
                  <div>
                    <strong>{row.category}</strong>
                    <span>{formatCompactMoney(row.spent, chartCurrency)} spent{remaining === null ? '' : ` · ${formatCompactMoney(remaining, chartCurrency)} left`}</span>
                  </div>
                  <input
                    min="0"
                    onChange={(event) => setBudgetDrafts((current) => ({ ...current, [row.category]: event.target.value }))}
                    placeholder="Monthly limit"
                    step="0.01"
                    type="number"
                    value={draft}
                  />
                  <button disabled={status === 'saving'} onClick={() => saveBudget(row.category, limit)} type="button">
                    {status === 'saving' ? 'Saving' : status === 'saved' ? 'Saved' : limit === null ? 'Set' : 'Update'}
                  </button>
                  {status === 'error' ? <small className="danger-text">error</small> : null}
                </div>
              );
            })}
          </div>
          {period === 'this_month' ? (
            <div className="jar-list budget-jar-list">
              {summary.jars.map((jar, index) => {
                const ratio = jar.ratio === null ? 0 : Math.min(jar.ratio, 1);
                return (
                  <div className="jar-row static" key={jar.id}>
                    <span className="jar-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                    <div>
                      <strong>{jar.label}</strong>
                      <small>{jar.limit > 0 ? `${formatCompactMoney(jar.remaining ?? 0, chartCurrency)} left` : 'no limit'}</small>
                    </div>
                    <em>{formatCompactMoney(jar.spent, chartCurrency)}</em>
                    <div className="jar-track">
                      <span className={`bar-fill ${ratioTone(jar.ratio)}`} style={{ width: `${Math.round(ratio * 100)}%` }} />
                    </div>
                    <small className="jar-limit">
                      {jar.limit > 0 ? `${formatCompactMoney(jar.spent, chartCurrency)} / ${formatCompactMoney(jar.limit, chartCurrency)}` : 'set budgets to use pressure'}
                    </small>
                  </div>
                );
              })}
            </div>
          ) : <EmptyState>Budget pressure is monthly. Switch range to Month to compare current spending with limits.</EmptyState>}
          <div className="accounts-net-reference"><span>Total</span><strong>{budgetEditorStatus === null ? 'No limits yet' : budgetEditorStatus >= 0 ? `${formatCompactMoney(budgetEditorStatus, chartCurrency)} left` : `${formatCompactMoney(Math.abs(budgetEditorStatus), chartCurrency)} over`}</strong><em>budgeting section</em></div>
        </Card>
      </div>
    </section>
  );
}
