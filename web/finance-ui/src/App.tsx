import { useEffect, useState } from 'react';
import { SovaProvider } from '@sova/kit';
import '@sova/kit/style.css';

import { AppShell } from './components/AppShell';
import type { NavItemId } from './config/navigation';
import { AccountsScreen } from './features/accounts/AccountsScreen';
import { OverviewScreen } from './features/overview/OverviewScreen';
import { initRuntime } from './lib/runtime';

export function App() {
  const [activeTab, setActiveTab] = useState<NavItemId>('overview');

  useEffect(() => {
    initRuntime();
  }, []);

  return (
    <SovaProvider theme="finance">
      <AppShell activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === 'accounts' ? <AccountsScreen /> : <OverviewScreen />}
      </AppShell>
    </SovaProvider>
  );
}
