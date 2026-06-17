import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { apiGet } from '../../api/client';
import type { Account, FxRate, MonthlyTrend } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { CHART_COLORS, convertAmount, shortMonth } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';

interface AccountsData {
  accounts: Account[];
  rates: FxRate[];
  trend: MonthlyTrend[];
}

function accountGroup(type: string, balance: number) {
  const normalized = type.toLowerCase();
  if (balance < 0 || normalized.includes('credit')) return 'Liabilities';
  if (normalized.includes('jar')) return 'Jars';
  if (normalized.includes('fop')) return 'FOP';
  return 'Cash';
}

export function AccountsScreen() {
  const { currency } = usePreferences();
  const [data, setData] = useState<AccountsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [accounts, rates, trend] = await Promise.all([
          apiGet<Account[]>('/accounts'),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
          apiGet<MonthlyTrend[]>('/transactions/trend?months=6').catch(() => []),
        ]);
        if (!cancelled) setData({ accounts, rates, trend });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const chartCurrency = currency === 'auto' ? data?.accounts[0]?.currency ?? 'UAH' : currency;
  const accounts = data?.accounts ?? [];
  const convertedAccounts = useMemo(
    () => accounts.map((account) => ({ ...account, convertedBalance: convertAmount(account.balance, account.currency, chartCurrency, data?.rates ?? []) })),
    [accounts, chartCurrency, data?.rates],
  );
  const totalBalance = convertedAccounts.reduce((sum, account) => sum + account.convertedBalance, 0);
  const assets = convertedAccounts.filter((account) => account.convertedBalance >= 0).reduce((sum, account) => sum + account.convertedBalance, 0);
  const liabilities = Math.abs(convertedAccounts.filter((account) => account.convertedBalance < 0).reduce((sum, account) => sum + account.convertedBalance, 0));
  const grouped = convertedAccounts.reduce<Record<string, typeof convertedAccounts>>((acc, account) => {
    const group = accountGroup(account.type, account.convertedBalance);
    acc[group] = [...(acc[group] ?? []), account];
    return acc;
  }, {});

  const chartRows = useMemo(() => {
    const monthlyNet = (data?.trend ?? []).map((row) => ({
      month: row.month,
      net: convertAmount(row.income - row.expenses, row.currency, chartCurrency, data?.rates ?? []),
    }));
    let running = totalBalance - monthlyNet.reduce((sum, row) => sum + row.net, 0);
    return monthlyNet.map((row) => {
      running += row.net;
      return { month: shortMonth(row.month), balance: Math.max(0, running) };
    });
  }, [chartCurrency, data?.rates, data?.trend, totalBalance]);

  const summaryGroups = Object.entries(grouped)
    .map(([name, rows]) => ({ name, total: rows.reduce((sum, row) => sum + Math.abs(row.convertedBalance), 0) }))
    .sort((a, b) => b.total - a.total);
  const summaryTotal = summaryGroups.reduce((sum, group) => sum + group.total, 0);

  return (
    <section className="dashboard-page monarch-page">
      <div className="section-head monarch-head">
        <div>
          <p className="eyebrow">Accounts</p>
          <h2>Balances and sync state</h2>
        </div>
        <div className="toolbar-row">
          <button className="soft-button" type="button">Refresh all</button>
          <button className="soft-button primary" type="button">Add account</button>
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}
      {!data && !error ? <LoadingState /> : null}
      {data ? (
        <>
          <Card className="net-worth-card" title="Net balance" subtitle={accounts.length ? `${accounts.length} synced accounts · ${chartCurrency}` : 'No synced accounts'}>
            <div className="net-worth-topline">
              <strong>{formatMoney(totalBalance, chartCurrency)}</strong>
              <span>{formatCompactMoney(assets, chartCurrency)} assets · {formatCompactMoney(liabilities, chartCurrency)} liabilities</span>
            </div>
            <div className="chart-frame account-area">
              {chartRows.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartRows} margin={{ left: 0, right: 10, top: 8, bottom: 0 }}>
                    <defs>
                      <linearGradient id="accountBalance" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#2a9d8f" stopOpacity="0.5" />
                        <stop offset="100%" stopColor="#2a9d8f" stopOpacity="0.04" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(14,15,12,0.07)" vertical={false} />
                    <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#6f726e', fontSize: 11 }} />
                    <YAxis hide domain={['dataMin', 'dataMax']} />
                    <Tooltip formatter={(value) => formatMoney(Number(value), chartCurrency)} contentStyle={{ borderRadius: 18 }} />
                    <Area dataKey="balance" fill="url(#accountBalance)" stroke="#2a9d8f" strokeWidth={3} type="monotone" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState>Sync more history to see a balance trend.</EmptyState>
              )}
            </div>
          </Card>

          <div className="accounts-layout">
            <div className="account-groups">
              {Object.entries(grouped).map(([group, rows], groupIndex) => (
                <Card className="account-group-card" key={group} title={group} subtitle={`${rows.length} accounts`}>
                  <div className="account-list">
                    {rows.map((account) => (
                      <div className="account-row" key={account.account_id}>
                        <div className="account-icon" style={{ background: CHART_COLORS[groupIndex % CHART_COLORS.length] }}>{account.name.slice(0, 1).toUpperCase()}</div>
                        <div>
                          <strong>{account.name}</strong>
                          <span>{account.type} · {account.synced_at ? `synced ${new Date(account.synced_at).toLocaleDateString()}` : 'not synced yet'}</span>
                        </div>
                        <em>{formatMoney(account.convertedBalance, chartCurrency)}</em>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>

            <Card className="account-summary-card" title="Summary" subtitle="Totals">
              <div className="summary-stack" aria-label="Account composition">
                {summaryGroups.map((group, index) => (
                  <span
                    key={group.name}
                    style={{
                      width: `${summaryTotal > 0 ? Math.max(4, (group.total / summaryTotal) * 100) : 0}%`,
                      background: CHART_COLORS[index % CHART_COLORS.length],
                    }}
                  />
                ))}
              </div>
              <div className="summary-list">
                {summaryGroups.map((group, index) => (
                  <div className="summary-row" key={group.name}>
                    <span><i style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />{group.name}</span>
                    <strong>{formatMoney(group.total, chartCurrency)}</strong>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </section>
  );
}
