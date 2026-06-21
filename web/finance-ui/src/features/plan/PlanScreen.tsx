import { SovaBadge, SovaKpiRow, SovaPageHeader } from '@sova/kit';
import { useEffect, useMemo, useState, type FormEvent } from 'react';

import { apiDelete, apiGet, apiPatch, apiPost } from '../../api/client';
import type { AccountsSummary, ForecastRow, FxRate, Goal, SpendingRow } from '../../api/types';
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
    title: 'Goals',
    description: 'Planned buys, savings pressure, affordability',
    goals: 'goals',
    target: 'Target',
    targetHint: 'planned buys',
    saved: 'Saved',
    left: 'Left',
    leftHint: 'to fund',
    canFundNow: 'Can fund now',
    liquidCovers: 'liquid covers goals',
    checkCash: 'check cash',
    addGoal: 'Add goal',
    addSubtitle: 'Planned purchase or savings target',
    plannedPurchases: 'Planned purchases',
    plannedSubtitle: 'Progress, monthly need, affordability',
    noGoals: 'No goals yet.',
    name: 'Name',
    namePlaceholder: 'Car, house, emergency fund',
    savedNow: 'Saved now',
    currency: 'Currency',
    deadline: 'Deadline',
    noDeadline: 'No deadline',
    saving: 'Saving',
    save: 'Save',
    savedStatus: 'saved',
    errorStatus: 'error',
    couldNotSave: 'Could not save',
    edit: 'Edit',
    update: 'Update',
    cancel: 'Cancel',
    delete: 'Delete',
    deleteConfirm: 'Delete this goal?',
    canAffordNow: 'Can afford now',
    needsSaving: 'Needs saving',
    noMonthlyPlan: 'No monthly plan',
    perMonth: 'mo',
    affordability: 'Affordability',
    forecastSignal: 'Forecast signal',
    liquidAfterDebt: 'Liquid after debt',
    goalsLeft: 'Goals left',
    afterAllGoals: 'After all goals',
    noForecast: 'No forecast yet.',
    forecast: 'Forecast',
  },
  uk: {
    eyebrow: 'фінанси',
    title: 'Цілі',
    description: 'Планові покупки, тиск заощаджень, доступність',
    goals: 'цілей',
    target: 'Ціль',
    targetHint: 'планові покупки',
    saved: 'Відкладено',
    left: 'Залишилось',
    leftHint: 'зібрати',
    canFundNow: 'Можу зараз',
    liquidCovers: 'ліквідні гроші покривають',
    checkCash: 'перевір гроші',
    addGoal: 'Додати ціль',
    addSubtitle: 'Планова покупка або заощадження',
    plannedPurchases: 'Планові покупки',
    plannedSubtitle: 'Прогрес, потреба на місяць, доступність',
    noGoals: 'Цілей ще немає.',
    name: 'Назва',
    namePlaceholder: 'Авто, житло, резерв',
    savedNow: 'Вже є',
    currency: 'Валюта',
    deadline: 'Дедлайн',
    noDeadline: 'Без дедлайну',
    saving: 'Зберігаю',
    save: 'Зберегти',
    savedStatus: 'збережено',
    errorStatus: 'помилка',
    couldNotSave: 'Не збереглося',
    edit: 'Змінити',
    update: 'Оновити',
    cancel: 'Скасувати',
    delete: 'Видалити',
    deleteConfirm: 'Видалити цю ціль?',
    canAffordNow: 'Можна купити зараз',
    needsSaving: 'Треба відкладати',
    noMonthlyPlan: 'Без місячного плану',
    perMonth: 'міс',
    affordability: 'Доступність',
    forecastSignal: 'Сигнал прогнозу',
    liquidAfterDebt: 'Ліквідні після боргу',
    goalsLeft: 'Залишилось на цілі',
    afterAllGoals: 'Після всіх цілей',
    noForecast: 'Прогнозу ще немає.',
    forecast: 'Прогноз',
  },
} as const;

type GoalLabels = (typeof labels)[keyof typeof labels];

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

function draftFromGoal(goal: Goal): GoalDraft {
  return {
    name: goal.name,
    target_amount: String(goal.target_amount),
    current_amount: String(goal.current_amount),
    currency: goal.currency,
    deadline: goal.deadline ?? '',
  };
}

function parseGoalDraft(draft: GoalDraft) {
  const targetAmount = Number(draft.target_amount);
  const currentAmount = draft.current_amount ? Number(draft.current_amount) : 0;
  if (!draft.name.trim() || !Number.isFinite(targetAmount) || targetAmount <= 0 || !Number.isFinite(currentAmount) || currentAmount < 0) {
    return null;
  }
  return {
    name: draft.name.trim(),
    target_amount: targetAmount,
    current_amount: currentAmount,
    currency: draft.currency,
    deadline: draft.deadline || null,
  };
}

function GoalFields({ draft, setDraft, text }: { draft: GoalDraft; setDraft: (updater: (current: GoalDraft) => GoalDraft) => void; text: GoalLabels }) {
  return (
    <>
      <label>
        <span>{text.name}</span>
        <input
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
          placeholder={text.namePlaceholder}
          required
          value={draft.name}
        />
      </label>
      <label>
        <span>{text.target}</span>
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
        <span>{text.savedNow}</span>
        <input
          min="0"
          onChange={(event) => setDraft((current) => ({ ...current, current_amount: event.target.value }))}
          step="0.01"
          type="number"
          value={draft.current_amount}
        />
      </label>
      <label>
        <span>{text.currency}</span>
        <select onChange={(event) => setDraft((current) => ({ ...current, currency: event.target.value }))} value={draft.currency}>
          <option value="UAH">UAH</option>
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
        </select>
      </label>
      <label>
        <span>{text.deadline}</span>
        <input onChange={(event) => setDraft((current) => ({ ...current, deadline: event.target.value }))} type="date" value={draft.deadline} />
      </label>
    </>
  );
}

function GoalForm({ currency, onCreated, text }: { currency: string; onCreated: (goal: Goal) => void; text: GoalLabels }) {
  const [draft, setDraft] = useState<GoalDraft>(() => emptyDraft(currency));
  const [status, setStatus] = useState<'idle' | 'saving' | 'error'>('idle');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = parseGoalDraft(draft);
    if (!payload) {
      setStatus('error');
      return;
    }
    setStatus('saving');
    try {
      const goal = await apiPost<Goal>('/goals', payload);
      onCreated(goal);
      setDraft(emptyDraft(currency));
      setStatus('idle');
    } catch {
      setStatus('error');
    }
  }

  return (
    <form className="goal-form" onSubmit={submit}>
      <GoalFields draft={draft} setDraft={setDraft} text={text} />
      <button disabled={status === 'saving'} type="submit">{status === 'saving' ? text.saving : text.addGoal}</button>
      {status === 'error' ? <small className="danger-text">{text.couldNotSave}</small> : null}
    </form>
  );
}

function SavedEditor({ goal, onSaved, text }: { goal: Goal; onSaved: (goal: Goal) => void; text: GoalLabels }) {
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
      <button disabled={status === 'saving'} onClick={save} type="button">{status === 'saving' ? '...' : text.save}</button>
      {status === 'saved' ? <small className="positive-text">{text.savedStatus}</small> : null}
      {status === 'error' ? <small className="danger-text">{text.errorStatus}</small> : null}
    </div>
  );
}

function GoalEditForm({ goal, onCancel, onDeleted, onSaved, text }: { goal: Goal; onCancel: () => void; onDeleted: (goalId: string) => void; onSaved: (goal: Goal) => void; text: GoalLabels }) {
  const [draft, setDraft] = useState<GoalDraft>(() => draftFromGoal(goal));
  const [status, setStatus] = useState<'idle' | 'saving' | 'error'>('idle');

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = parseGoalDraft(draft);
    if (!payload) {
      setStatus('error');
      return;
    }
    setStatus('saving');
    try {
      const patched = await apiPatch<Goal>(`/goals/${goal.id}`, payload);
      onSaved(patched);
      setStatus('idle');
      onCancel();
    } catch {
      setStatus('error');
    }
  }

  async function deleteGoal() {
    if (!window.confirm(text.deleteConfirm)) return;
    setStatus('saving');
    try {
      await apiDelete<{ deleted: boolean }>(`/goals/${goal.id}`);
      onDeleted(goal.id);
    } catch {
      setStatus('error');
    }
  }

  return (
    <form className="goal-edit-form" onSubmit={save}>
      <GoalFields draft={draft} setDraft={setDraft} text={text} />
      <div className="goal-edit-actions">
        <button disabled={status === 'saving'} type="submit">{status === 'saving' ? text.saving : text.update}</button>
        <button className="ghost" onClick={onCancel} type="button">{text.cancel}</button>
        <button className="danger" disabled={status === 'saving'} onClick={deleteGoal} type="button">{text.delete}</button>
        {status === 'error' ? <small className="danger-text">{text.couldNotSave}</small> : null}
      </div>
    </form>
  );
}

export function PlanScreen() {
  const { currency, language } = usePreferences();
  const text = labels[language];
  const [data, setData] = useState<PlanData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingGoalId, setEditingGoalId] = useState<string | null>(null);

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

  function removeGoal(goalId: string) {
    setData((current) => {
      if (!current) return current;
      return { ...current, goals: current.goals.filter((goal) => goal.id !== goalId) };
    });
    setEditingGoalId(null);
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <section className="dashboard-page goals-page">
      <div className="sova-surface-band finance-operator-band">
        <SovaPageHeader
          eyebrow={text.eyebrow}
          title={text.title}
          description={`${text.description} · ${displayCurrency}`}
          meta={<SovaBadge tone={urgentGoals ? 'warn' : 'accent'}>{data.goals.length} {text.goals}</SovaBadge>}
        />
        <SovaKpiRow
          items={[
            { label: text.target, value: formatCompactMoney(totals.target, displayCurrency), hint: text.targetHint, tone: 'accent' },
            { label: text.saved, value: formatCompactMoney(totals.saved, displayCurrency), hint: `${totals.progress}%`, tone: 'good' },
            { label: text.left, value: formatCompactMoney(totals.left, displayCurrency), hint: text.leftHint, tone: 'neutral' },
            { label: text.canFundNow, value: formatCompactMoney(Math.max(0, liquid), displayCurrency), hint: afterGoals >= 0 ? text.liquidCovers : text.checkCash, tone: afterGoals >= 0 ? 'good' : 'warn' },
          ]}
        />
      </div>

      <div className="analytics-grid goals-grid">
        <Card className="wide" title={text.addGoal} subtitle={text.addSubtitle}>
          <GoalForm currency={displayCurrency} onCreated={upsertGoal} text={text} />
        </Card>

        <Card className="wide" title={text.plannedPurchases} subtitle={text.plannedSubtitle}>
          {data.goals.length === 0 ? <EmptyState>{text.noGoals}</EmptyState> : null}
          <div className="goal-list">
            {data.goals.map((goal) => {
              const progress = goalProgress(goal);
              const left = Math.max(0, goal.target_amount - goal.current_amount);
              const months = monthsUntil(goal.deadline);
              const monthlyNeed = months ? left / months : null;
              const leftInDisplay = convertAmount(left, goal.currency, displayCurrency, data.rates);
              const affordable = liquid >= leftInDisplay;
              if (editingGoalId === goal.id) {
                return (
                  <div className="goal-row editing" key={goal.id}>
                    <GoalEditForm goal={goal} onCancel={() => setEditingGoalId(null)} onDeleted={removeGoal} onSaved={upsertGoal} text={text} />
                  </div>
                );
              }
              return (
                <div className="goal-row detailed" key={goal.id}>
                  <div>
                    <strong>{goal.name}</strong>
                    <span>{goal.deadline ? `${text.deadline} ${goal.deadline}` : text.noDeadline}</span>
                  </div>
                  <div className="goal-progress">
                    <div className="goal-track"><span style={{ width: `${progress}%` }} /></div>
                    <small>{progress}% · {formatMoney(left, goal.currency)} {text.left.toLowerCase()}</small>
                  </div>
                  <div className="goal-pressure">
                    <span className={affordable ? 'positive-text' : 'muted-text'}>{affordable ? text.canAffordNow : text.needsSaving}</span>
                    <strong>{monthlyNeed === null ? text.noMonthlyPlan : `${formatCompactMoney(monthlyNeed, goal.currency)} / ${text.perMonth}`}</strong>
                  </div>
                  <SavedEditor goal={goal} onSaved={upsertGoal} text={text} />
                  <div className="goal-row-actions">
                    <button onClick={() => setEditingGoalId(goal.id)} type="button">{text.edit}</button>
                  </div>
                  <em>{formatMoney(goal.current_amount, goal.currency)} / {formatMoney(goal.target_amount, goal.currency)}</em>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title={text.affordability} subtitle={text.forecastSignal}>
          <div className="summary-list">
            <div className="summary-row"><span>{text.liquidAfterDebt}</span><strong>{formatMoney(liquid, displayCurrency)}</strong></div>
            <div className="summary-row"><span>{text.goalsLeft}</span><strong>{formatMoney(totals.left, displayCurrency)}</strong></div>
            <div className="summary-row"><span>{text.afterAllGoals}</span><strong className={liquid - totals.left >= 0 ? 'positive-text' : 'danger-text'}>{formatMoney(liquid - totals.left, displayCurrency)}</strong></div>
          </div>
          {data.forecast.length === 0 ? <EmptyState>{text.noForecast}</EmptyState> : null}
          <div className="summary-list forecast-list">
            {data.forecast.slice(0, 6).map((row, index) => (
              <div className="summary-row" key={`${row.date ?? 'row'}-${index}`}>
                <span>{row.label ?? row.date ?? text.forecast}</span>
                <strong>{formatMoney(row.amount ?? row.balance ?? 0, row.currency ?? displayCurrency)}</strong>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
}
