import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState, type FormEvent } from 'react';

import { apiGet, apiPost } from '../../api/client';
import type { Account, AccountsSummary, FxRate, IncomeTotal, ManualBalance, SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { convertAmount, preferredCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';

const labels = {
  en: {
    eyebrow: 'finance',
    title: 'Accounts',
    description: 'Bank, cash, ownership, debt',
    bank: 'Bank',
    cash: 'Cash',
    ownership: 'Ownership',
    debt: 'Debt',
    earned: 'Earned',
    netSmall: 'Net reference',
    accounts: 'accounts',
    bankAccounts: 'Bank accounts',
    syncedBalances: 'Synced balances',
    cashTitle: 'Cash',
    manualCash: 'Manual cash',
    ownershipTitle: 'Ownership',
    assetsSubtitle: 'Assets · own value',
    debtTitle: 'Debt',
    debtSubtitle: 'Cards + manual debt',
    earningsTitle: 'Earnings',
    earningsSubtitle: 'Revenue signal',
    month: 'This month',
    year: 'This year',
    noBank: 'No bank accounts synced.',
    noCash: 'No cash added.',
    noAssets: 'No assets added.',
    noDebt: 'No debts added.',
    fop: 'FOP',
    spent: 'spent',
    netHint: 'small only',
    addTitle: 'Add manual row',
    addSubtitle: 'Cash, ownership, debt',
    type: 'Type',
    currency: 'Currency',
    name: 'Name',
    amount: 'Amount',
    add: 'Add',
    saving: 'Saving',
    saved: 'Saved',
    saveFailed: 'Could not save',
    ownershipPercent: 'Ownership %',
    note: 'Note',
    cashOption: 'Cash',
    assetOption: 'Ownership',
    debtOption: 'Debt',
  },
  uk: {
    eyebrow: 'фінанси',
    title: 'Рахунки',
    description: 'Банк, готівка, власність, борги',
    bank: 'Банк',
    cash: 'Готівка',
    ownership: 'Власність',
    debt: 'Борг',
    earned: 'Заробив',
    netSmall: 'Нетто довідково',
    accounts: 'рахунків',
    bankAccounts: 'Банківські рахунки',
    syncedBalances: 'Синхронізовані баланси',
    cashTitle: 'Готівка',
    manualCash: 'Ручна готівка',
    ownershipTitle: 'Власність',
    assetsSubtitle: 'Активи · твоя частка',
    debtTitle: 'Борг',
    debtSubtitle: 'Картки + ручні борги',
    earningsTitle: 'Дохід',
    earningsSubtitle: 'Сигнал виручки',
    month: 'Цей місяць',
    year: 'Цей рік',
    noBank: 'Банківські рахунки ще не синхронізовані.',
    noCash: 'Готівку ще не додано.',
    noAssets: 'Активи ще не додано.',
    noDebt: 'Борги ще не додано.',
    fop: 'ФОП',
    spent: 'витрачено',
    netHint: 'маленько',
    addTitle: 'Додати вручну',
    addSubtitle: 'Готівка, власність, борг',
    type: 'Тип',
    currency: 'Валюта',
    name: 'Назва',
    amount: 'Сума',
    add: 'Додати',
    saving: 'Зберігаю',
    saved: 'Збережено',
    saveFailed: 'Не збереглося',
    ownershipPercent: 'Частка %',
    note: 'Нотатка',
    cashOption: 'Готівка',
    assetOption: 'Власність',
    debtOption: 'Борг',
  },
} as const;

type AccountsLabels = (typeof labels)[keyof typeof labels];
type ManualKind = ManualBalance['kind'];

interface ManualBalanceDraft {
  kind: ManualKind;
  name: string;
  currency: string;
  amount: string;
  ownership_percent: string;
  note: string;
}

const emptyDraft = (currency: string): ManualBalanceDraft => ({
  kind: 'cash',
  name: '',
  currency: currency === 'auto' ? 'UAH' : currency,
  amount: '',
  ownership_percent: '100',
  note: '',
});

interface AccountsData {
  summary: AccountsSummary;
  rates: FxRate[];
}

function manualValue(row: ManualBalance) {
  if (row.kind === 'asset') return row.amount * (row.ownership_percent / 100);
  return row.amount;
}

function rowsFromData(summary: AccountsSummary): SpendingRow[] {
  const bankRows = summary.bank_accounts.map((account) => ({
    category: `bank:${account.account_id}`,
    currency: account.currency,
    amount: Math.abs(account.balance),
  }));
  const manualRows = summary.manual_balances.map((row) => ({
    category: `${row.kind}:${row.id}`,
    currency: row.currency,
    amount: manualValue(row),
  }));
  const incomeRows = [...summary.earnings.month, ...summary.earnings.year].map((row, index) => ({
    category: `income:${index}`,
    currency: row.currency,
    amount: row.amount,
  }));
  return [...bankRows, ...manualRows, ...incomeRows].filter((row) => row.amount > 0);
}

function sumConverted<T>(rows: T[], getAmount: (row: T) => number, getCurrency: (row: T) => string, currency: string, rates: FxRate[]) {
  return rows.reduce((sum, row) => sum + convertAmount(getAmount(row), getCurrency(row), currency, rates), 0);
}

function incomeTotal(rows: IncomeTotal[], currency: string, rates: FxRate[]) {
  return sumConverted(rows, (row) => row.amount, (row) => row.currency, currency, rates);
}

function AccountList({ accounts, currency, rates, text }: { accounts: Account[]; currency: string; rates: FxRate[]; text: AccountsLabels }) {
  if (accounts.length === 0) return <EmptyState>{text.noBank}</EmptyState>;
  return (
    <div className="account-list">
      {accounts.map((account) => {
        const displayBalance = convertAmount(account.balance, account.currency, currency, rates);
        return (
          <div className="account-row" key={account.account_id}>
            <div className="account-icon">{account.name.slice(0, 1).toUpperCase()}</div>
            <div>
              <strong>{account.name}</strong>
              <span>{account.type}{account.is_fop ? ` · ${text.fop}` : ''}{account.spent ? ` · ${formatCompactMoney(account.spent, account.currency)} ${text.spent}` : ''}</span>
            </div>
            <em className={displayBalance < 0 ? 'danger-text' : ''}>{formatMoney(displayBalance, currency)}</em>
          </div>
        );
      })}
    </div>
  );
}

function ManualList({ empty, rows, currency, rates }: { empty: string; rows: ManualBalance[]; currency: string; rates: FxRate[] }) {
  if (rows.length === 0) return <EmptyState>{empty}</EmptyState>;
  return (
    <div className="account-list">
      {rows.map((row) => {
        const value = manualValue(row);
        const displayValue = convertAmount(value, row.currency, currency, rates);
        return (
          <div className="account-row" key={row.id}>
            <div className={`account-icon ${row.kind}`}>{row.kind === 'cash' ? '₴' : row.kind === 'asset' ? 'A' : 'D'}</div>
            <div>
              <strong>{row.name}</strong>
              <span>{row.currency}{row.kind === 'asset' && row.ownership_percent !== 100 ? ` · ${row.ownership_percent}%` : ''}</span>
            </div>
            <em className={row.kind === 'debt' ? 'danger-text' : ''}>{formatMoney(displayValue, currency)}</em>
          </div>
        );
      })}
    </div>
  );
}

function ManualBalanceForm({ currency, onCreated, text }: { currency: string; onCreated: () => Promise<void>; text: AccountsLabels }) {
  const [draft, setDraft] = useState<ManualBalanceDraft>(() => emptyDraft(currency));
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('saving');
    try {
      await apiPost<ManualBalance>('/accounts/manual-balances', {
        kind: draft.kind,
        name: draft.name.trim(),
        currency: draft.currency,
        amount: Number(draft.amount),
        ownership_percent: draft.kind === 'asset' ? Number(draft.ownership_percent) : 100,
        note: draft.note.trim() || null,
      });
      setDraft(emptyDraft(currency));
      await onCreated();
      setStatus('saved');
      window.setTimeout(() => setStatus('idle'), 1800);
    } catch {
      setStatus('error');
    }
  }

  return (
    <form className="manual-balance-form" onSubmit={submit}>
      <label>
        <span>{text.type}</span>
        <select
          onChange={(event) => setDraft((current) => ({ ...current, kind: event.target.value as ManualKind }))}
          value={draft.kind}
        >
          <option value="cash">{text.cashOption}</option>
          <option value="asset">{text.assetOption}</option>
          <option value="debt">{text.debtOption}</option>
        </select>
      </label>
      <label className="manual-form-name">
        <span>{text.name}</span>
        <input
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
          placeholder={draft.kind === 'asset' ? 'Car' : draft.kind === 'debt' ? 'Loan' : 'Cash'}
          required
          value={draft.name}
        />
      </label>
      <label>
        <span>{text.amount}</span>
        <input
          min="0"
          onChange={(event) => setDraft((current) => ({ ...current, amount: event.target.value }))}
          required
          step="0.01"
          type="number"
          value={draft.amount}
        />
      </label>
      <label>
        <span>{text.currency}</span>
        <select
          onChange={(event) => setDraft((current) => ({ ...current, currency: event.target.value }))}
          value={draft.currency}
        >
          <option value="UAH">UAH</option>
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
        </select>
      </label>
      {draft.kind === 'asset' ? (
        <label>
          <span>{text.ownershipPercent}</span>
          <input
            max="100"
            min="0"
            onChange={(event) => setDraft((current) => ({ ...current, ownership_percent: event.target.value }))}
            step="1"
            type="number"
            value={draft.ownership_percent}
          />
        </label>
      ) : null}
      <label className="manual-form-note">
        <span>{text.note}</span>
        <input
          onChange={(event) => setDraft((current) => ({ ...current, note: event.target.value }))}
          value={draft.note}
        />
      </label>
      <button disabled={status === 'saving'} type="submit">
        {status === 'saving' ? text.saving : text.add}
      </button>
      {status === 'saved' ? <small className="positive-text">{text.saved}</small> : null}
      {status === 'error' ? <small className="danger-text">{text.saveFailed}</small> : null}
    </form>
  );
}

export function AccountsScreen() {
  const { currency, language } = usePreferences();
  const text = labels[language];
  const [data, setData] = useState<AccountsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reloadSummary() {
    const summary = await apiGet<AccountsSummary>('/accounts/summary');
    setData((current) => (current ? { ...current, summary } : { summary, rates: [] }));
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [summary, rates] = await Promise.all([
          apiGet<AccountsSummary>('/accounts/summary'),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
        ]);
        if (!cancelled) setData({ summary, rates });
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unknown error');
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const displayCurrency = useMemo(() => {
    if (!data) return currency === 'auto' ? 'UAH' : currency;
    return preferredCurrency(rowsFromData(data.summary), currency);
  }, [currency, data]);

  const totals = useMemo(() => {
    const summary = data?.summary;
    const rates = data?.rates ?? [];
    if (!summary) {
      return { bank: 0, cash: 0, ownership: 0, debt: 0, earnedMonth: 0, earnedYear: 0, net: 0 };
    }
    const positiveBank = summary.bank_accounts.filter((account) => account.balance > 0);
    const negativeBank = summary.bank_accounts.filter((account) => account.balance < 0);
    const cashRows = summary.manual_balances.filter((row) => row.kind === 'cash');
    const ownershipRows = summary.manual_balances.filter((row) => row.kind === 'asset');
    const debtRows = summary.manual_balances.filter((row) => row.kind === 'debt');

    const bank = sumConverted(positiveBank, (row) => row.balance, (row) => row.currency, displayCurrency, rates);
    const cash = sumConverted(cashRows, manualValue, (row) => row.currency, displayCurrency, rates);
    const ownership = sumConverted(ownershipRows, manualValue, (row) => row.currency, displayCurrency, rates);
    const cardDebt = sumConverted(negativeBank, (row) => Math.abs(row.balance), (row) => row.currency, displayCurrency, rates);
    const manualDebt = sumConverted(debtRows, manualValue, (row) => row.currency, displayCurrency, rates);
    const debt = cardDebt + manualDebt;
    const earnedMonth = incomeTotal(summary.earnings.month, displayCurrency, rates);
    const earnedYear = incomeTotal(summary.earnings.year, displayCurrency, rates);
    return { bank, cash, ownership, debt, earnedMonth, earnedYear, net: bank + cash + ownership - debt };
  }, [data, displayCurrency]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  const cashRows = data.summary.manual_balances.filter((row) => row.kind === 'cash');
  const ownershipRows = data.summary.manual_balances.filter((row) => row.kind === 'asset');
  const manualDebtRows = data.summary.manual_balances.filter((row) => row.kind === 'debt');
  const cardDebtRows = data.summary.bank_accounts.filter((account) => account.balance < 0);
  const debtRows = [
    ...manualDebtRows,
    ...cardDebtRows.map<ManualBalance>((account) => ({
      id: account.account_id,
      kind: 'debt',
      name: account.name,
      currency: account.currency,
      amount: Math.abs(account.balance),
      ownership_percent: 100,
      note: account.type,
    })),
  ];

  return (
    <section className="dashboard-page accounts-page">
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow={text.eyebrow}
          title={text.title}
          description={`${text.description} · ${displayCurrency}`}
          meta={<SovaBadge tone="accent">{data.summary.bank_accounts.length} {text.accounts}</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: text.bank, value: formatCompactMoney(totals.bank, displayCurrency), hint: displayCurrency, tone: 'accent' },
            { label: text.cash, value: formatCompactMoney(totals.cash, displayCurrency), hint: `${cashRows.length}`, tone: 'good' },
            { label: text.ownership, value: formatCompactMoney(totals.ownership, displayCurrency), hint: `${ownershipRows.length}`, tone: 'neutral' },
            { label: text.debt, value: formatCompactMoney(totals.debt, displayCurrency), hint: `${debtRows.length}`, tone: 'warn' },
            { label: text.earned, value: formatCompactMoney(totals.earnedMonth, displayCurrency), hint: text.month, tone: 'good' },
          ]}
        />
        <div className="accounts-net-reference">
          <span>{text.netSmall}</span>
          <strong>{formatMoney(totals.net, displayCurrency)}</strong>
          <em>{text.netHint}</em>
        </div>
      </div>

      <div className="analytics-grid accounts-grid">
        <Card className="wide" title={text.addTitle} subtitle={text.addSubtitle}>
          <ManualBalanceForm currency={displayCurrency} onCreated={reloadSummary} text={text} />
        </Card>
        <Card className="wide" title={text.bankAccounts} subtitle={text.syncedBalances}>
          <AccountList accounts={data.summary.bank_accounts} currency={displayCurrency} rates={data.rates} text={text} />
        </Card>
        <Card title={text.cashTitle} subtitle={text.manualCash}>
          <ManualList empty={text.noCash} rows={cashRows} currency={displayCurrency} rates={data.rates} />
        </Card>
        <Card title={text.ownershipTitle} subtitle={text.assetsSubtitle}>
          <ManualList empty={text.noAssets} rows={ownershipRows} currency={displayCurrency} rates={data.rates} />
        </Card>
        <Card title={text.debtTitle} subtitle={text.debtSubtitle} tone={debtRows.length ? 'warning' : 'default'}>
          <ManualList empty={text.noDebt} rows={debtRows} currency={displayCurrency} rates={data.rates} />
        </Card>
        <Card className="wide" title={text.earningsTitle} subtitle={text.earningsSubtitle}>
          <div className="summary-list">
            <div className="summary-row"><span>{text.month}</span><strong>{formatMoney(totals.earnedMonth, displayCurrency)}</strong></div>
            <div className="summary-row"><span>{text.year}</span><strong>{formatMoney(totals.earnedYear, displayCurrency)}</strong></div>
          </div>
        </Card>
      </div>
    </section>
  );
}
