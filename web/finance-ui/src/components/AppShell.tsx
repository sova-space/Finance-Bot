import { SovaBadge, SovaBrand, SovaButton, SovaNav, SovaShell, SovaTopbar } from '@sova/kit';
import { useState, type ReactNode } from 'react';

import { apiPost } from '../api/client';
import { NAV_ITEMS, type NavItemId } from '../config/navigation';
import { usePreferences, type CurrencyPreference, type LabelKey } from '../lib/preferences';
import { lightFeedback } from '../lib/runtime';

interface AppShellProps {
  activeTab: NavItemId;
  children: ReactNode;
  onTabChange: (tab: NavItemId) => void;
}

const NAV_LABEL_KEYS: Record<NavItemId, LabelKey> = {
  overview: 'navOverview',
  accounts: 'navAccounts',
  spending: 'navSpending',
  goals: 'navGoals',
};

const TITLE_KEYS: Record<NavItemId, LabelKey> = {
  overview: 'titleOverview',
  accounts: 'titleAccounts',
  spending: 'titleSpending',
  goals: 'titleGoals',
};

const currencies: CurrencyPreference[] = ['auto', 'UAH', 'USD', 'EUR'];

export function AppShell({ activeTab, children, onTabChange }: AppShellProps) {
  const { currency, language, setCurrency, setLanguage, t } = usePreferences();
  const [syncState, setSyncState] = useState<'idle' | 'syncing' | 'done' | 'error'>('idle');

  async function triggerSync() {
    setSyncState('syncing');
    try {
      await apiPost('/sync');
      setSyncState('done');
      window.setTimeout(() => setSyncState('idle'), 2400);
    } catch {
      setSyncState('error');
      window.setTimeout(() => setSyncState('idle'), 3200);
    }
  }

  const syncLabel = syncState === 'syncing' ? 'Syncing' : syncState === 'done' ? 'Synced' : syncState === 'error' ? 'Failed' : 'Sync';

  return (
    <SovaShell
      sidebar={
        <>
          <SovaBrand mark="₴" eyebrow={t('financeBot')} title={t('moneyOs')} />
          <SovaNav
            items={NAV_ITEMS.map((item) => ({
              label: t(NAV_LABEL_KEYS[item.id]),
              active: activeTab === item.id,
              icon: <span aria-hidden="true">{item.glyph}</span>,
              onClick: () => {
                lightFeedback();
                onTabChange(item.id);
              },
            }))}
          />
          <div className="sidebar-note">
            <span className="status-dot" />
            {t('liveData')}
          </div>
        </>
      }
    >
      <SovaTopbar
        eyebrow={t('analytics')}
        title={t(TITLE_KEYS[activeTab])}
        actions={
          <>
            <div className="mini-switch" aria-label={t('language')}>
              <button className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')} type="button">EN</button>
              <button className={language === 'uk' ? 'active' : ''} onClick={() => setLanguage('uk')} type="button">UA</button>
            </div>
            <select
              aria-label={t('currency')}
              className="mini-select"
              onChange={(event) => setCurrency(event.target.value as CurrencyPreference)}
              value={currency}
            >
              {currencies.map((item) => (
                <option key={item} value={item}>{item === 'auto' ? t('auto') : item}</option>
              ))}
            </select>
            <SovaButton
              className={`mini-sync ${syncState}`}
              disabled={syncState === 'syncing'}
              onClick={triggerSync}
              type="button"
              variant="primary"
            >
              {syncLabel}
            </SovaButton>
            {syncState === 'done' ? <SovaBadge tone="good">OK</SovaBadge> : null}
            {syncState === 'error' ? <SovaBadge tone="bad">Error</SovaBadge> : null}
          </>
        }
      />
      {children}
    </SovaShell>
  );
}
