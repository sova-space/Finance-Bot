import { useEffect, useState } from 'react';
import { SovaProvider } from '@sova/kit';
import '@sova/kit/style.css';

import { AppShell } from './components/AppShell';
import type { NavItemId } from './config/navigation';
import { AccountsScreen } from './features/accounts/AccountsScreen';
import { CashflowScreen as SpendingScreen } from './features/cashflow/CashflowScreen';
import { OverviewScreen } from './features/overview/OverviewScreen';
import { PlanScreen as GoalsScreen } from './features/plan/PlanScreen';
import { initRuntime } from './lib/runtime';

export function App() {
  const [activeTab, setActiveTab] = useState<NavItemId>('overview');

  useEffect(() => {
    initRuntime();
  }, []);

  return (
    <SovaProvider theme="finance">
      <AppShell activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === 'accounts' ? (
          <AccountsScreen />
        ) : activeTab === 'spending' ? (
          <SpendingScreen />
        ) : activeTab === 'goals' ? (
          <GoalsScreen />
        ) : (
          <OverviewScreen />
        )}
      </AppShell>
    </SovaProvider>
  );
}
