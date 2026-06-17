import { useEffect, useState } from 'react';

import { AppShell } from './components/AppShell';
import type { NavItemId } from './config/navigation';
import { AccountsScreen } from './features/accounts/AccountsScreen';
import { BudgetScreen } from './features/budget/BudgetScreen';
import { OverviewScreen } from './features/overview/OverviewScreen';
import { PlanScreen } from './features/plan/PlanScreen';
import { SpendingScreen } from './features/spending/SpendingScreen';
import { TransactionsScreen } from './features/transactions/TransactionsScreen';
import { initRuntime } from './lib/runtime';

export function App() {
  const [activeTab, setActiveTab] = useState<NavItemId>('overview');

  useEffect(() => {
    initRuntime();
  }, []);

  return (
    <AppShell activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'overview' ? <OverviewScreen /> : null}
      {activeTab === 'spending' ? <SpendingScreen /> : null}
      {activeTab === 'transactions' ? <TransactionsScreen /> : null}
      {activeTab === 'accounts' ? <AccountsScreen /> : null}
      {activeTab === 'budget' ? <BudgetScreen /> : null}
      {activeTab === 'plan' ? <PlanScreen /> : null}
    </AppShell>
  );
}
