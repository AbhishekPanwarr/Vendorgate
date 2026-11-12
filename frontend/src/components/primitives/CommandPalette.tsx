import React, { useState, useEffect, useRef } from 'react';
import { Search, LayoutDashboard, FileText, CheckSquare, Users, BarChart2, BookOpen, AlertCircle, Wrench, ArrowRight, Star } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Kbd } from './Kbd';

interface CommandItem {
  id: string;
  category: 'Navigation' | 'Actions' | 'Cases' | 'Vendors' | 'Admin';
  title: string;
  subtitle?: string;
  shortcut?: string;
  icon: React.ReactNode;
  action: () => void;
  starred?: boolean;
}

export const CommandPalette: React.FC = () => {
  const { isCommandPaletteOpen, setCommandPaletteOpen, navigate, cases, runs, setRole, advanceVirtualClock } = useApp();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isCommandPaletteOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isCommandPaletteOpen]);

  const allItems: CommandItem[] = [
    // Navigation
    {
      id: 'nav-dashboard',
      category: 'Navigation',
      title: 'Dashboard',
      subtitle: 'Overview KPIs, pipeline runs, and triage analytics',
      shortcut: 'G D',
      icon: <LayoutDashboard size={16} />,
      action: () => navigate('/'),
      starred: true
    },
    {
      id: 'nav-submit',
      category: 'Navigation',
      title: 'Submit vendor',
      subtitle: 'Open vendor intake portal with document verifications',
      shortcut: 'G S',
      icon: <FileText size={16} />,
      action: () => navigate('/submit'),
      starred: true
    },
    {
      id: 'nav-approvals',
      category: 'Navigation',
      title: 'Approvals queue',
      subtitle: 'Triage pending submissions across AP, Controller, and Compliance',
      shortcut: 'G A',
      icon: <CheckSquare size={16} />,
      action: () => navigate('/approvals'),
      starred: true
    },
    {
      id: 'nav-vendors',
      category: 'Navigation',
      title: 'Vendors directory',
      subtitle: 'Master vendor records and attribute network graph',
      shortcut: 'G V',
      icon: <Users size={16} />,
      action: () => navigate('/vendors')
    },
    {
      id: 'nav-benchmark',
      category: 'Navigation',
      title: 'Benchmark & honesty report',
      subtitle: 'Evaluations against 109 critical cases and ablation studies',
      shortcut: 'G B',
      icon: <BarChart2 size={16} />,
      action: () => navigate('/benchmark')
    },
    {
      id: 'nav-policy',
      category: 'Navigation',
      title: 'Policy specifications',
      subtitle: 'Assumptions A-01..A-15 and scoring thresholds',
      shortcut: 'G P',
      icon: <BookOpen size={16} />,
      action: () => navigate('/policy')
    },
    {
      id: 'nav-foolit',
      category: 'Navigation',
      title: 'Fool-it Adversarial Lab',
      subtitle: 'Execute mutation operators to test pipeline resilience',
      shortcut: 'G F',
      icon: <AlertCircle size={16} />,
      action: () => navigate('/foolit')
    },
    {
      id: 'nav-admin',
      category: 'Navigation',
      title: 'Admin control room',
      subtitle: 'Virtual clock, fault injections, and system reset',
      icon: <Wrench size={16} />,
      action: () => navigate('/admin')
    },

    // Actions
    {
      id: 'act-role-controller',
      category: 'Actions',
      title: 'Switch role to Controller',
      subtitle: 'Unlock dual-controller approvals and spend authorization',
      icon: <CheckSquare size={16} />,
      action: () => setRole('Controller')
    },
    {
      id: 'act-role-ap',
      category: 'Actions',
      title: 'Switch role to AP Analyst',
      subtitle: 'Triage queue for vendor tax and bank verifications',
      icon: <CheckSquare size={16} />,
      action: () => setRole('AP Analyst')
    },
    {
      id: 'act-clock-advance',
      category: 'Actions',
      title: 'Advance virtual clock +7 days',
      subtitle: 'Trigger expiration nudges and aging deadlines',
      icon: <Wrench size={16} />,
      action: () => advanceVirtualClock(7)
    },

    // Dynamic Cases
    ...cases.slice(0, 4).map(c => ({
      id: `case-${c.id}`,
      category: 'Cases' as const,
      title: `${c.vendorName} (${c.id})`,
      subtitle: `Status: ${c.status} · Score: ${c.score} · ${c.country}`,
      icon: <FileText size={16} />,
      action: () => navigate(`/cases/${c.id}`)
    })),

    // Dynamic Runs
    ...runs.slice(0, 3).map(r => ({
      id: `run-${r.id}`,
      category: 'Actions' as const,
      title: `View Run: ${r.vendorName}`,
      subtitle: `${r.id} · ${r.status} (${r.durationMs}ms)`,
      icon: <ArrowRight size={16} />,
      action: () => navigate(`/runs/${r.id}`)
    }))
  ];

  const filteredItems = allItems.filter(item => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q) ||
      (item.subtitle && item.subtitle.toLowerCase().includes(q))
    );
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % filteredItems.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredItems.length) % filteredItems.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
        setCommandPaletteOpen(false);
      }
    } else if (e.key === 'Escape') {
      setCommandPaletteOpen(false);
    }
  };

  if (!isCommandPaletteOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={() => setCommandPaletteOpen(false)}
      className="fixed inset-0 z-50 flex justify-center pt-[15vh] px-4 bg-black/40 dark:bg-black/60 backdrop-blur-[4px] animate-in fade-in-0 duration-120"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="w-full max-w-[640px] rounded-[12px] border border-border bg-surface text-text-primary shadow-lg dark:shadow-none overflow-hidden h-fit max-h-[70vh] flex flex-col animate-in zoom-in-95 duration-180 ease-[cubic-bezier(0.16,1,0.3,1)]"
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-border-subtle bg-surface">
          <Search size={18} className="text-text-tertiary shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search anything (cases, vendors, actions, routes)…"
            className="w-full bg-transparent text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none"
          />
          <Kbd>ESC</Kbd>
        </div>

        {/* Results List */}
        <div className="p-2 overflow-y-auto divide-y divide-border-subtle/50">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-text-tertiary text-[13px]">
              No results found for "{query}".
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.action();
                    setCommandPaletteOpen(false);
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`h-10 px-3 flex items-center justify-between rounded-[6px] text-[13px] cursor-pointer transition-colors duration-60 ${
                    isSelected ? 'bg-subtle text-text-primary' : 'text-text-secondary'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <span className="text-text-tertiary">{item.icon}</span>
                    <span className="font-medium text-text-primary truncate">
                      {item.title}
                    </span>
                    {item.subtitle && (
                      <span className="text-[12px] text-text-tertiary truncate hidden sm:inline">
                        — {item.subtitle}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {item.starred && <Star size={13} className="text-accent fill-accent" />}
                    {item.shortcut ? (
                      <Kbd>{item.shortcut}</Kbd>
                    ) : (
                      <span className="text-[11px] text-text-tertiary uppercase font-mono">
                        {item.category}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
