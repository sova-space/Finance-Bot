import { useState, type ReactNode } from 'react';

import { apiPost } from '../api/client';
import { NAV_ITEMS, type NavItemId } from '../config/navigation';
import { usePreferences, type CurrencyPreference } from '../lib/preferences';
import { lightFeedback } from '../lib/runtime';

interface AppShellProps {
  activeTab: NavItemId;
  children: ReactNode;
  onTabChange: (tab: NavItemId) => void;
}

const navLabelKey: Record<NavItemId, 'navOverview' | 'navSpending' | 'navBudget' | 'navPlan'> = {
  overview: 'navOverview',
  spending: 'navSpending',
  budget: 'navBudget',
  plan: 'navPlan',
};

const titleKey: Record<NavItemId, 'titleOverview' | 'titleSpending' | 'titleBudget' | 'titlePlan'> = {
  overview: 'titleOverview',
  spending: 'titleSpending',
  budget: 'titleBudget',
  plan: 'titlePlan',
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
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">₴</div>
          <div>
            <p className="eyebrow">{t('financeBot')}</p>
            <strong>{t('moneyOs')}</strong>
          </div>
        </div>

        <nav className="side-nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <button
              aria-current={activeTab === item.id ? 'page' : undefined}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              key={item.id}
              onClick={() => {
                lightFeedback();
                onTabChange(item.id);
              }}
              type="button"
            >
              <span className="nav-glyph" aria-hidden="true">{item.glyph}</span>
              <span>{t(navLabelKey[item.id])}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="status-dot" />
          {t('liveData')}
        </div>
      </aside>

      <main className="app-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">{t('analytics')}</p>
            <h1>{t(titleKey[activeTab])}</h1>
          </div>
          <div className="topbar-actions">
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
            <button
              className={`mini-sync ${syncState}`}
              disabled={syncState === 'syncing'}
              onClick={triggerSync}
              type="button"
            >
              {syncLabel}
            </button>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
