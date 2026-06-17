import type { ReactNode } from 'react';

import { NAV_ITEMS, type NavItemId } from '../config/navigation';
import { lightFeedback } from '../lib/runtime';

interface AppShellProps {
  activeTab: NavItemId;
  children: ReactNode;
  onTabChange: (tab: NavItemId) => void;
}

export function AppShell({ activeTab, children, onTabChange }: AppShellProps) {
  const activeItem = NAV_ITEMS.find((item) => item.id === activeTab) ?? NAV_ITEMS[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">₴</div>
          <div>
            <p className="eyebrow">Finance Bot</p>
            <strong>Money OS</strong>
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
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="status-dot" />
          Live Monobank data
        </div>
      </aside>

      <main className="app-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Analytics</p>
            <h1>{activeItem.title}</h1>
          </div>
          <div className="topbar-pill">Personal finance</div>
        </header>
        {children}
      </main>
    </div>
  );
}
