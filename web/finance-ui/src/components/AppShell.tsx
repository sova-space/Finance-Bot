import type { ReactNode } from 'react';

import { NAV_ITEMS, type NavItemId } from '../config/navigation';
import { lightFeedback } from '../lib/runtime';

interface AppShellProps {
  activeTab: NavItemId;
  children: ReactNode;
  onTabChange: (tab: NavItemId) => void;
}

export function AppShell({ activeTab, children, onTabChange }: AppShellProps) {
  return (
    <div className="app-shell">
      <main className="app-content">{children}</main>
      <nav className="tab-bar" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <button
            aria-current={activeTab === item.id ? 'page' : undefined}
            className={`tab ${activeTab === item.id ? 'active' : ''}`}
            key={item.id}
            onClick={() => {
              lightFeedback();
              onTabChange(item.id);
            }}
            type="button"
          >
            <span className="tab-icon" aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
