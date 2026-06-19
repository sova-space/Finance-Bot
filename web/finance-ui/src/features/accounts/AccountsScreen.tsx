import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState, type FormEvent } from 'react';

import { apiDelete, apiGet, apiPatch, apiPost } from '../../api/client';
import type { Account, AccountsSummary, FxRate, ManualBalance, SpendingRow } from '../../api/types';
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
    title: 'What do I have',
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
    addTitle: 'Edit manual',
    addSubtitle: 'Rare setup action',
    closeManual: 'Close',
    type: 'Type',
    currency: 'Currency',
    name: 'Name',
    amount: 'Amount',
    add: 'Add',
    update: 'Update',
    edit: 'Edit',
    delete: 'Delete',
    cancel: 'Cancel',
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
    title: 'Що я маю',
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
    addTitle: 'Редагувати вручну',
    addSubtitle: 'Рідкісне налаштування',
    closeManual: 'Закрити',
    type: 'Тип',
    currency: 'Валюта',
    name: 'Назва',
    amount: 'Сума',
    add: 'Додати',
    update: 'Оновити',
    edit: 'Змінити',
    delete: 'Видалити',
    cancel: 'Скасувати',
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

const draftFromManualBalance = (row: ManualBalance): ManualBalanceDraft => ({
  kind: row.kind,
  name: row.name,
  currency: row.currency,
  amount: String(row.amount),
  ownership_percent: String(row.ownership_percent),
  note: row.note ?? '',
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
  return [...bankRows, ...manualRows].filter((row) => row.amount > 0);
}

function sumConverted<T>(rows: T[], getAmount: (row: T) => number, getCurrency: (row: T) => string, currency: string, rates: FxRate[]) {
  return rows.reduce((sum, row) => sum + convertAmount(getAmount(row), getCurrency(row), currency, rates), 0);
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

function ManualList({
  canEdit = false,
  currency,
  empty,
  onChanged,
  rates,
  rows,
  text,
}: {
  canEdit?: boolean;
  currency: string;
  empty: string;
  onChanged?: () => Promise<void>;
  rates: FxRate[];
  rows: ManualBalance[];
  text: AccountsLabels;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ManualBalanceDraft | null>(null);
  const [status, setStatus] = useState<Record<string, 'saving' | 'saved' | 'error'>>({});

  function startEdit(row: ManualBalance) {
    setEditingId(row.id);
    setDraft(draftFromManualBalance(row));
  }

  async function saveEdit(row: ManualBalance) {
    if (!draft || !onChanged) return;
    setStatus((current) => ({ ...current, [row.id]: 'saving' }));
    try {
      await apiPatch<ManualBalance>(`/accounts/manual-balances/${row.id}`, {
        kind: draft.kind,
        name: draft.name.trim(),
        currency: draft.currency,
        amount: Number(draft.amount),
        ownership_percent: draft.kind === 'asset' ? Number(draft.ownership_percent) : 100,
        note: draft.note.trim() || null,
      });
      await onChanged();
      setEditingId(null);
      setDraft(null);
      setStatus((current) => ({ ...current, [row.id]: 'saved' }));
      window.setTimeout(() => setStatus((current) => {
        const next = { ...current };
        delete next[row.id];
        return next;
      }), 1000);
    } catch {
      setStatus((current) => ({ ...current, [row.id]: 'error' }));
    }
  }

  async function deleteRow(row: ManualBalance) {
    if (!onChanged) return;
    setStatus((current) => ({ ...current, [row.id]: 'saving' }));
    try {
      await apiDelete<{ deleted: boolean }>(`/accounts/manual-balances/${row.id}`);
      await onChanged();
      setEditingId(null);
      setDraft(null);
    } catch {
      setStatus((current) => ({ ...current, [row.id]: 'error' }));
    }
  }

  if (rows.length === 0) return <EmptyState>{empty}</EmptyState>;
  return (
    <div className="account-list">
      {rows.map((row) => {
        const value = manualValue(row);
        const displayValue = convertAmount(value, row.currency, currency, rates);
        const editing = editingId === row.id && draft;
        return (
          <div className={`account-row ${canEdit ? 'editable' : ''}`} key={row.id}>
            <div className={`account-icon ${row.kind}`}>{row.kind === 'cash' ? '₴' : row.kind === 'asset' ? 'A' : 'D'}</div>
            {editing ? (
              <div className="manual-row-editor">
                <select onChange={(event) => setDraft((current) => current ? { ...current, kind: event.target.value as ManualKind } : current)} value={draft.kind}>
                  <option value="cash">{text.cashOption}</option>
                  <option value="asset">{text.assetOption}</option>
                  <option value="debt">{text.debtOption}</option>
                </select>
                <input onChange={(event) => setDraft((current) => current ? { ...current, name: event.target.value } : current)} value={draft.name} />
                <input min="0" onChange={(event) => setDraft((current) => current ? { ...current, amount: event.target.value } : current)} step="0.01" type="number" value={draft.amount} />
                <select onChange={(event) => setDraft((current) => current ? { ...current, currency: event.target.value } : current)} value={draft.currency}>
                  <option value="UAH">UAH</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                </select>
                {draft.kind === 'asset' ? <input max="100" min="0" onChange={(event) => setDraft((current) => current ? { ...current, ownership_percent: event.target.value } : current)} step="1" type="number" value={draft.ownership_percent} /> : null}
                <input onChange={(event) => setDraft((current) => current ? { ...current, note: event.target.value } : current)} placeholder={text.note} value={draft.note} />
              </div>
            ) : (
              <div>
                <strong>{row.name}</strong>
                <span>{row.currency}{row.kind === 'asset' && row.ownership_percent !== 100 ? ` · ${row.ownership_percent}%` : ''}</span>
              </div>
            )}
            <em className={row.kind === 'debt' ? 'danger-text' : ''}>{formatMoney(displayValue, currency)}</em>
            {canEdit ? (
              <div className="manual-row-actions">
                {editing ? (
                  <>
                    <button disabled={status[row.id] === 'saving'} onClick={() => saveEdit(row)} type="button">{status[row.id] === 'saving' ? text.saving : text.update}</button>
                    <button className="ghost" onClick={() => { setEditingId(null); setDraft(null); }} type="button">{text.cancel}</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => startEdit(row)} type="button">{text.edit}</button>
                    <button className="danger" disabled={status[row.id] === 'saving'} onClick={() => deleteRow(row)} type="button">{text.delete}</button>
                  </>
                )}
                {status[row.id] === 'error' ? <small className="danger-text">{text.saveFailed}</small> : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function AccountsDiagram({ totals, currency, text }: { totals: { bank: number; cash: number; ownership: number; debt: number }; currency: string; text: AccountsLabels }) {
  const rows = [
    { label: text.bank, value: totals.bank, tone: 'bank' },
    { label: text.cash, value: totals.cash, tone: 'cash' },
    { label: text.ownership, value: totals.ownership, tone: 'asset' },
    { label: text.debt, value: totals.debt, tone: 'debt' },
  ].filter((row) => row.value > 0);
  const max = Math.max(...rows.map((row) => row.value), 1);
  return (
    <div className="accounts-diagram">
      {rows.length === 0 ? <EmptyState>{text.noBank}</EmptyState> : rows.map((row) => (
        <div className="accounts-diagram-row" key={row.label}>
          <div>
            <span>{row.label}</span>
            <strong>{formatMoney(row.value, currency)}</strong>
          </div>
          <div className="accounts-diagram-track">
            <i className={row.tone} style={{ width: `${Math.max(6, (row.value / max) * 100)}%` }} />
          </div>
        </div>
      ))}
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
  const [manualEditorOpen, setManualEditorOpen] = useState(false);

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
      return { bank: 0, cash: 0, ownership: 0, debt: 0, net: 0 };
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
    return { bank, cash, ownership, debt, net: bank + cash + ownership - debt };
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
          ]}
        />
        <div className="accounts-net-reference">
          <span>{text.netSmall}</span>
          <strong>{formatMoney(totals.net, displayCurrency)}</strong>
          <em>{text.netHint}</em>
          <button onClick={() => setManualEditorOpen((open) => !open)} type="button">
            {manualEditorOpen ? text.closeManual : text.addTitle}
          </button>
        </div>
      </div>

      <div className="analytics-grid accounts-grid">
        {manualEditorOpen ? (
          <Card className="wide" title={text.addTitle} subtitle={text.addSubtitle}>
            <ManualBalanceForm currency={displayCurrency} onCreated={reloadSummary} text={text} />
          </Card>
        ) : null}
        <Card className="wide" title="Money structure" subtitle={`${text.bank} / ${text.cash} / ${text.ownership} / ${text.debt}`}>
          <AccountsDiagram totals={totals} currency={displayCurrency} text={text} />
        </Card>
        <Card className="wide" title={text.bankAccounts} subtitle={text.syncedBalances}>
          <AccountList accounts={data.summary.bank_accounts} currency={displayCurrency} rates={data.rates} text={text} />
        </Card>
        <Card title={text.cashTitle} subtitle={text.manualCash}>
          <ManualList canEdit empty={text.noCash} onChanged={reloadSummary} rows={cashRows} currency={displayCurrency} rates={data.rates} text={text} />
        </Card>
        <Card title={text.ownershipTitle} subtitle={text.assetsSubtitle}>
          <ManualList canEdit empty={text.noAssets} onChanged={reloadSummary} rows={ownershipRows} currency={displayCurrency} rates={data.rates} text={text} />
        </Card>
        <Card title={text.debtTitle} subtitle={text.debtSubtitle} tone={debtRows.length ? 'warning' : 'default'}>
          {debtRows.length === 0 ? <EmptyState>{text.noDebt}</EmptyState> : null}
          {cardDebtRows.length > 0 ? <AccountList accounts={cardDebtRows} currency={displayCurrency} rates={data.rates} text={text} /> : null}
          {manualDebtRows.length > 0 ? <ManualList canEdit empty={text.noDebt} onChanged={reloadSummary} rows={manualDebtRows} currency={displayCurrency} rates={data.rates} text={text} /> : null}
        </Card>
      </div>
    </section>
  );
}
