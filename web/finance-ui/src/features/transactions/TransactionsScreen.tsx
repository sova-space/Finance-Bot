import { useEffect, useMemo, useState } from 'react';

import { apiGet } from '../../api/client';
import type { FxRate, TransactionItem } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { PeriodSelector } from '../../components/PeriodSelector';
import type { AnalyticsPeriod } from '../../config/periods';
import { convertAmount } from '../../lib/chartData';
import { formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';

interface TransactionsData {
  rates: FxRate[];
  transactions: TransactionItem[];
}

function groupByDate(rows: TransactionItem[]) {
  return rows.reduce<Record<string, TransactionItem[]>>((groups, row) => {
    groups[row.date] = [...(groups[row.date] ?? []), row];
    return groups;
  }, {});
}

export function TransactionsScreen() {
  const { currency } = usePreferences();
  const [period, setPeriod] = useState<AnalyticsPeriod>('this_month');
  const [query, setQuery] = useState('');
  const [data, setData] = useState<TransactionsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    async function load() {
      try {
        const [transactions, rates] = await Promise.all([
          apiGet<TransactionItem[]>(`/transactions?period=${period}&limit=200`),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
        ]);
        if (!cancelled) setData({ transactions, rates });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const chartCurrency = currency === 'auto' ? data?.transactions[0]?.currency ?? 'UAH' : currency;
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const rows = data?.transactions ?? [];
    if (!needle) return rows;
    return rows.filter((tx) => [tx.description, tx.category, tx.mode, tx.date].some((value) => value?.toLowerCase().includes(needle)));
  }, [data?.transactions, query]);
  const grouped = groupByDate(filtered);
  const converted = filtered.map((tx) => convertAmount(tx.amount, tx.currency, chartCurrency, data?.rates ?? []));
  const income = converted.filter((amount) => amount > 0).reduce((sum, amount) => sum + amount, 0);
  const spending = Math.abs(converted.filter((amount) => amount < 0).reduce((sum, amount) => sum + amount, 0));
  const largestIncome = Math.max(0, ...converted);
  const largestExpense = Math.abs(Math.min(0, ...converted));
  const average = converted.length ? converted.reduce((sum, amount) => sum + amount, 0) / converted.length : 0;
  const dates = filtered.map((tx) => tx.date).sort();

  return (
    <section className="dashboard-page monarch-page">
      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Source of truth</p>
          <h2>Transactions</h2>
        </div>
        <div className="toolbar-row">
          <input
            className="search-input"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search"
            type="search"
            value={query}
          />
          <PeriodSelector value={period} onChange={setPeriod} />
          <button className="soft-button" type="button">Filters</button>
          <button className="soft-button" type="button">Edit rules</button>
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}
      {!data && !error ? <LoadingState /> : null}
      {data ? (
        <div className="transactions-layout">
          <Card className="transactions-card" title="All transactions" subtitle={`${filtered.length} rows · ${chartCurrency}`}>
            {filtered.length === 0 ? (
              <EmptyState>No transactions match this view.</EmptyState>
            ) : (
              <div className="transaction-groups">
                {Object.entries(grouped).map(([date, rows]) => (
                  <div className="transaction-date-group" key={date}>
                    <div className="date-row"><strong>{date}</strong><span>{rows.length} tx</span></div>
                    {rows.map((tx, index) => {
                      const amount = convertAmount(tx.amount, tx.currency, chartCurrency, data.rates);
                      return (
                        <button className="transaction-row" key={`${date}-${tx.description}-${index}`} type="button">
                          <div className="merchant-cell">
                            <strong>{tx.description}</strong>
                            <span>{tx.mode ?? 'Card'}</span>
                          </div>
                          <span className="category-pill">{tx.category ?? 'Uncategorized'}</span>
                          <span className="account-pill">{tx.is_pending ? 'Pending' : 'Posted'}</span>
                          <em className={amount > 0 ? 'positive' : ''}>{formatMoney(amount, chartCurrency)}</em>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="transaction-summary" title="Summary" subtitle={period.replace('_', ' ')}>
            <div className="summary-list">
              <div className="summary-row"><span>Total transactions</span><strong>{filtered.length}</strong></div>
              <div className="summary-row"><span>Largest income</span><strong className="positive-text">{formatMoney(largestIncome, chartCurrency)}</strong></div>
              <div className="summary-row"><span>Largest expense</span><strong>{formatMoney(largestExpense, chartCurrency)}</strong></div>
              <div className="summary-row"><span>Average transaction</span><strong>{formatMoney(average, chartCurrency)}</strong></div>
              <div className="summary-row"><span>Total income</span><strong className="positive-text">{formatMoney(income, chartCurrency)}</strong></div>
              <div className="summary-row"><span>Total spending</span><strong>{formatMoney(spending, chartCurrency)}</strong></div>
              <div className="summary-row"><span>First transaction</span><strong>{dates[0] ?? '—'}</strong></div>
              <div className="summary-row"><span>Last transaction</span><strong>{dates.at(-1) ?? '—'}</strong></div>
            </div>
            <button className="download-button" type="button">Download CSV</button>
          </Card>
        </div>
      ) : null}
    </section>
  );
}
