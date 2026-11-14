import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  badge?: number | string;
  icon?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = '' }) => {
  return (
    <div className={`relative border-b border-border w-full ${className}`}>
      <div
        role="tablist"
        className="flex items-center gap-6 overflow-x-auto no-scrollbar"
      >
        {tabs.map(tab => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onChange(tab.id)}
              className={`relative h-9 flex items-center gap-2 text-[13px] font-medium transition-colors duration-120 whitespace-nowrap cursor-pointer focus-ring ${
                isActive
                  ? 'text-text-primary'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`text-[11px] px-1.5 py-0.2 rounded-full font-mono tabular ${
                    isActive
                      ? 'bg-accent-subtle text-accent-fg'
                      : 'bg-subtle text-text-tertiary'
                  }`}
                >
                  {tab.badge}
                </span>
              )}

              {/* Shared layout underline animation indicator */}
              {isActive && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent transition-all duration-180 ease-[cubic-bezier(0.16,1,0.3,1)]"
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
