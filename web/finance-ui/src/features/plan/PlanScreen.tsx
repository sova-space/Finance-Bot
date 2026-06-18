import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState, type FormEvent } from 'react';

import { apiGet, apiPatch, apiPost } from '../../api/client';
import type { AccountsSummary, ForecastRow, FxRate, Goal, SpendingRow } from '../../api/types';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { convertAmount, preferredCurrency } from '../../lib/chartData';
import { formatCompactMoney, formatMoney } from '../../lib/formatMoney';
import { usePreferences } from '../../lib/preferences';

interface PlanData {
  goals: Goal[];
  forecast: ForecastRow[];
  accounts: AccountsSummary | null;
  rates: FxRate[];
}

interface GoalDraft {
  name: string;
  target_amount: string;
  current_amount: string;
  currency: string;
  deadline: string;
}

function goalProgress(goal: Goal) {
  if (goal.target_amount <= 0) return 0;
  return Math.min(100, Math.round((goal.current_amount / goal.target_amount) * 100));
}

function monthsUntil(deadline?: string | null) {
  if (!deadline) return null;
  const target = new Date(`${deadline}T00:00:00`);
  if (Number.isNaN(target.getTime())) return null;
  const now = new Date();
  const months = (target.getFullYear() - now.getFullYear()) * 12 + target.getMonth() - now.getMonth();
  return Math.max(1, months + 1);
}

function manualValue(row: AccountsSummary['manual_balances'][number]) {
  if (row.kind === 'asset') return row.amount * (row.ownership_percent / 100);
  return row.amount;
}

function accountRows(summary: AccountsSummary | null): SpendingRow[] {
  if (!summary) return [];
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

function liquidAmount(summary: AccountsSummary | null, currency: string, rates: FxRate[]) {
  if (!summary) return 0;
  const bank = summary.bank_accounts.reduce(
    (sum, account) => sum + convertAmount(account.balance, account.currency, currency, rates),
    0,
  );
  const cash = summary.manual_balances
    .filter((row) => row.kind === 'cash')
    .reduce((sum, row) => sum + convertAmount(row.amount, row.currency, currency, rates), 0);
  const debt = summary.manual_balances
    .filter((row) => row.kind === 'debt')
    .reduce((sum, row) => sum + convertAmount(row.amount, row.currency, currency, rates), 0);
  return bank + cash - debt;
}

function emptyDraft(currency: string): GoalDraft {
  return {
    name: '',
    target_amount: '',
    current_amount: '',
    currency,
    deadline: '',
  };
}

function GoalForm({ currency, onCreated }: { currency: string; onCreated: (goal: Goal) => void }) {
  const [draft, setDraft] = useState<GoalDraft>(() => emptyDraft(currency));
  const [status, setStatus] = useState<'idle' | 'saving' | 'error'>('idle');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('saving');
    try {
      const targetAmount = Number(draft.target_amount);
      const currentAmount = draft.current_amount ? Number(draft.current_amount) : 0;
      if (!Number.isFinite(targetAmount) || targetAmount <= 0 || !Number.isFinite(currentAmount) || currentAmount < 0) {
        setStatus('error');
        return;
      }
      const goal = await apiPost<Goal>('/goals', {
        name: draft.name.trim(),
        target_amount: targetAmount,
        current_amount: currentAmount,
        currency: draft.currency,
        deadline: draft.deadline || null,
      });
      onCreated(goal);
      setDraft(emptyDraft(currency));
      setStatus('idle');
    } catch {
      setStatus('error');
    }
  }

  return (
    <form className="goal-form" onSubmit={submit}>
      <label>
        <span>Name</span>
        <input
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
          placeholder="Car, house, emergency fund"
          required
          value={draft.name}
        />
      </label>
      <label>
        <span>Target</span>
        <input
          min="0"
          onChange={(event) => setDraft((current) => ({ ...current, target_amount: event.target.value }))}
          required
          step="0.01"
          type="number"
          value={draft.target_amount}
        />
      </label>
      <label>
        <span>Saved now</span>
        <input
          min="0"
          onChange={(event) => setDraft((current) => ({ ...current, current_amount: event.target.value }))}
          step="0.01"
          type="number"
          value={draft.current_amount}
        />
      </label>
      <label>
        <span>Currency</span>
        <select onChange={(event) => setDraft((current) => ({ ...current, currency: event.target.value }))} value={draft.currency}>
          <option value="UAH">UAH</option>
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
        </select>
      </label>
      <label>
        <span>Deadline</span>
        <input onChange={(event) => setDraft((current) => ({ ...current, deadline: event.target.value }))} type="date" value={draft.deadline} />
      </label>
      <button disabled={status === 'saving'} type="submit">{status === 'saving' ? 'Saving' : 'Add goal'}</button>
      {status === 'error' ? <small className="danger-text">Could not save</small> : null}
    </form>
  );
}

function SavedEditor({ goal, onSaved }: { goal: Goal; onSaved: (goal: Goal) => void }) {
  const [amount, setAmount] = useState(String(goal.current_amount));
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  useEffect(() => {
    setAmount(String(goal.current_amount));
  }, [goal.current_amount]);

  async function save() {
    const nextAmount = Number(amount);
    if (!Number.isFinite(nextAmount) || nextAmount < 0) {
      setStatus('error');
      return;
    }
    setStatus('saving');
    try {
      const patched = await apiPatch<Goal>(`/goals/${goal.id}`, { current_amount: nextAmount });
      onSaved(patched);
      setStatus('saved');
      window.setTimeout(() => setStatus('idle'), 1400);
    } catch {
      setStatus('error');
    }
  }

  return (
    <div className="goal-saved-editor">
      <input min="0" onChange={(event) => setAmount(event.target.value)} step="0.01" type="number" value={amount} />
      <button disabled={status === 'saving'} onClick={save} type="button">{status === 'saving' ? '...' : 'Save'}</button>
      {status === 'saved' ? <small className="positive-text">saved</small> : null}
      {status === 'error' ? <small className="danger-text">error</small> : null}
    </div>
  );
}

export function PlanScreen() {
  const { currency } = usePreferences();
  const [data, setData] = useState<PlanData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [goals, forecast, accounts, rates] = await Promise.all([
          apiGet<Goal[]>('/goals'),
          apiGet<ForecastRow[]>('/forecast'),
          apiGet<AccountsSummary>('/accounts/summary').catch(() => null),
          apiGet<FxRate[]>('/fx/rates').catch(() => []),
        ]);
        if (!cancelled) setData({ goals, forecast, accounts, rates });
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
    const goalRows = data?.goals.map((goal) => ({ category: goal.name, currency: goal.currency, amount: goal.target_amount })) ?? [];
    return preferredCurrency([...goalRows, ...accountRows(data?.accounts ?? null)], currency);
  }, [currency, data?.accounts, data?.goals]);

  const totals = useMemo(() => {
    const goals = data?.goals ?? [];
    const rates = data?.rates ?? [];
    const target = goals.reduce((sum, goal) => sum + convertAmount(goal.target_amount, goal.currency, displayCurrency, rates), 0);
    const saved = goals.reduce((sum, goal) => sum + convertAmount(goal.current_amount, goal.currency, displayCurrency, rates), 0);
    return { target, saved, left: Math.max(0, target - saved), progress: target > 0 ? Math.round((saved / target) * 100) : 0 };
  }, [data?.goals, data?.rates, displayCurrency]);

  const liquid = useMemo(() => liquidAmount(data?.accounts ?? null, displayCurrency, data?.rates ?? []), [data?.accounts, data?.rates, displayCurrency]);
  const afterGoals = liquid - totals.left;
  const urgentGoals = (data?.goals ?? []).filter((goal) => {
    const months = monthsUntil(goal.deadline);
    return months !== null && months <= 3 && goal.current_amount < goal.target_amount;
  }).length;

  function upsertGoal(goal: Goal) {
    setData((current) => {
      if (!current) return current;
      const exists = current.goals.some((row) => row.id === goal.id);
      return { ...current, goals: exists ? current.goals.map((row) => (row.id === goal.id ? goal : row)) : [goal, ...current.goals] };
    });
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page goals-page">
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow="finance"
          title="Goals"
          description={`Planned buys, savings pressure, affordability · ${displayCurrency}`}
          meta={<SovaBadge tone={urgentGoals ? 'warn' : 'accent'}>{data.goals.length} goals</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: 'Target', value: formatCompactMoney(totals.target, displayCurrency), hint: 'planned buys', tone: 'accent' },
            { label: 'Saved', value: formatCompactMoney(totals.saved, displayCurrency), hint: `${totals.progress}%`, tone: 'good' },
            { label: 'Left', value: formatCompactMoney(totals.left, displayCurrency), hint: 'to fund', tone: 'neutral' },
            { label: 'Can fund now', value: formatCompactMoney(Math.max(0, liquid), displayCurrency), hint: afterGoals >= 0 ? 'liquid covers goals' : 'check cash', tone: afterGoals >= 0 ? 'good' : 'warn' },
          ]}
        />
      </div>

      <div className="analytics-grid goals-grid">
        <Card className="wide" title="Add goal" subtitle="Planned purchase or savings target">
          <GoalForm currency={displayCurrency} onCreated={upsertGoal} />
        </Card>

        <Card className="wide" title="Planned purchases" subtitle="Progress, monthly need, affordability">
          {data.goals.length === 0 ? <EmptyState>No goals yet.</EmptyState> : null}
          <div className="goal-list">
            {data.goals.map((goal) => {
              const progress = goalProgress(goal);
              const left = Math.max(0, goal.target_amount - goal.current_amount);
              const months = monthsUntil(goal.deadline);
              const monthlyNeed = months ? left / months : null;
              const leftInDisplay = convertAmount(left, goal.currency, displayCurrency, data.rates);
              const affordable = liquid >= leftInDisplay;
              return (
                <div className="goal-row detailed" key={goal.id}>
                  <div>
                    <strong>{goal.name}</strong>
                    <span>{goal.deadline ? `Deadline ${goal.deadline}` : 'No deadline'}</span>
                  </div>
                  <div className="goal-progress">
                    <div className="goal-track"><span style={{ width: `${progress}%` }} /></div>
                    <small>{progress}% · {formatMoney(left, goal.currency)} left</small>
                  </div>
                  <div className="goal-pressure">
                    <span className={affordable ? 'positive-text' : 'muted-text'}>{affordable ? 'Can afford now' : 'Needs saving'}</span>
                    <strong>{monthlyNeed === null ? 'No monthly plan' : `${formatCompactMoney(monthlyNeed, goal.currency)} / mo`}</strong>
                  </div>
                  <SavedEditor goal={goal} onSaved={upsertGoal} />
                  <em>{formatMoney(goal.current_amount, goal.currency)} / {formatMoney(goal.target_amount, goal.currency)}</em>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="Affordability" subtitle="Forecast signal">
          <div className="summary-list">
            <div className="summary-row"><span>Liquid after debt</span><strong>{formatMoney(liquid, displayCurrency)}</strong></div>
            <div className="summary-row"><span>Goals left</span><strong>{formatMoney(totals.left, displayCurrency)}</strong></div>
            <div className="summary-row"><span>After all goals</span><strong className={liquid - totals.left >= 0 ? 'positive-text' : 'danger-text'}>{formatMoney(liquid - totals.left, displayCurrency)}</strong></div>
          </div>
          {data.forecast.length === 0 ? <EmptyState>No forecast yet.</EmptyState> : null}
          <div className="summary-list forecast-list">
            {data.forecast.slice(0, 6).map((row, index) => (
              <div className="summary-row" key={`${row.date ?? 'row'}-${index}`}>
                <span>{row.label ?? row.date ?? 'Forecast'}</span>
                <strong>{formatMoney(row.amount ?? row.balance ?? 0, row.currency ?? displayCurrency)}</strong>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
}
