import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Button } from '../components/primitives/Button';
import { Input } from '../components/primitives/Input';
import { Badge } from '../components/primitives/Badge';
import { useApp } from '../context/AppContext';
import { Clock, AlertTriangle, RotateCcw, Wrench, ShieldAlert } from 'lucide-react';

export const AdminPage: React.FC = () => {
  const { role, setRole, virtualNow, advanceVirtualClock, clockHistory, faults, setFault, resetAllData } = useApp();

  const [advanceDays, setAdvanceDays] = useState(7);
  const [resetConfirmText, setResetConfirmText] = useState('');
  const [localFaults, setLocalFaults] = useState(faults);

  const adapters = ['Registry', 'IRS', 'GST', 'VIES', 'Bank', 'LLM'];

  const handleApplyFaults = () => {
    Object.entries(localFaults).forEach(([ad, cfg]) => {
      setFault(ad, cfg.status, cfg.ttl);
    });
  };

  const handleReset = () => {
    if (resetConfirmText.trim() === 'RESET') {
      resetAllData();
      setResetConfirmText('');
    }
  };

  return (
    <div className="py-6 flex justify-center animate-in fade-in-0 duration-240">
      <div className="w-full max-w-[720px] space-y-8">
        <PageHeader
          title="Admin Control Room"
          description="Operational time-travel, adapter fault injection, and deterministic seed resets."
        />

        {/* Security Role Warning if not ADMIN */}
        {role !== 'Admin' && (
          <div className="p-4 rounded-[8px] bg-warning-subtle border border-warning/30 flex items-center justify-between text-[13px]">
            <div className="flex items-center gap-2 text-warning">
              <ShieldAlert size={16} />
              <span>You are viewing this panel as <span className="font-semibold">{role}</span>.</span>
            </div>
            <Button size="sm" variant="secondary" onClick={() => setRole('Admin')}>
              Switch to Admin Role
            </Button>
          </div>
        )}

        {/* Card 1: Virtual Clock */}
        <Card padding="compact" title="1. Virtual Time Machine">
          <div className="space-y-4 pt-1 text-[13px]">
            <div>
              <span className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary block">
                Current Virtual Now
              </span>
                <div className="text-[24px] font-mono font-semibold text-text-primary tabular my-1">
                  {virtualNow || '—'}
                </div>
            </div>

            <div className="flex items-end gap-3 pt-2">
              <div className="w-48">
                <Input
                  label="Advance by N days"
                  type="number"
                  min={1}
                  value={advanceDays}
                  onChange={e => setAdvanceDays(Math.max(1, Number(e.target.value) || 1))}
                  variant="number"
                />
              </div>
              <Button
                variant="primary"
                leftIcon={<Clock size={14} />}
                onClick={() => advanceVirtualClock(advanceDays)}
              >
                Advance
              </Button>
            </div>

            <p className="text-[12px] text-text-tertiary leading-normal">
              This fires scheduler jobs: 14-day vendor response expiration deadlines, lifecycle reminder nudges, and insurance renewal verifications.
            </p>

            {/* History of clock advances */}
            <div className="pt-3 border-t border-border-subtle space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-text-tertiary">
                Recent Time Advances
              </span>
              <div className="space-y-1">
                {clockHistory.slice(0, 5).map((h, idx) => (
                  <div key={idx} className="flex justify-between text-[12px] text-text-secondary font-mono">
                    <span>+{h.daysAdded} days</span>
                    <span className="text-text-primary">{h.newDate}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Card 2: Fault Injection (display only — no server endpoint) */}
        <Card padding="compact" title="2. Adapter Fault Injection (display only)">
          <div className="space-y-4 pt-1 text-[13px]">
            <p className="text-[12px] text-text-secondary">
              Local panel only: the server exposes no fault-injection endpoint. Real adapter faults live in backend/tests/chaos. Toggling here changes the panel state, not pipeline behavior.
            </p>

            <div className="space-y-3">
              {adapters.map(adapter => {
                const cur = localFaults[adapter] || { status: 'Off', ttl: 300 };

                return (
                  <div key={adapter} className="p-3 rounded-[6px] bg-subtle/40 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="font-semibold text-text-primary text-[13px] w-28">
                      {adapter} API
                    </span>

                    {/* Segmented Control: Off · Timeout · Error · Slow */}
                    <div className="flex items-center bg-surface p-0.5 rounded-[6px] border border-border">
                      {(['Off', 'Timeout', 'Error', 'Slow'] as const).map(st => (
                        <button
                          key={st}
                          type="button"
                          onClick={() => setLocalFaults(p => ({ ...p, [adapter]: { ...cur, status: st } }))}
                          className={`h-7 px-2.5 rounded-[4px] text-[11px] font-medium transition-colors cursor-pointer ${
                            cur.status === st
                              ? st === 'Off'
                                ? 'bg-subtle text-text-primary shadow-xs'
                                : 'bg-warning text-white'
                              : 'text-text-secondary hover:text-text-primary'
                          }`}
                        >
                          {st}
                        </button>
                      ))}
                    </div>

                    <div className="flex items-center gap-1.5 text-[12px]">
                      <span className="text-text-tertiary">TTL:</span>
                      <input
                        type="number"
                        value={cur.ttl}
                        onChange={e => {
                          const ttlVal = Number(e.target.value) || 300;
                          setLocalFaults(p => ({ ...p, [adapter]: { ...cur, ttl: ttlVal } }));
                        }}
                        className="w-16 h-7 rounded border border-border bg-surface px-1.5 text-center font-mono tabular"
                      />
                      <span className="text-text-tertiary">s</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[12px] text-text-tertiary">Faults persist for TTL duration or until cleared.</span>
              <Button size="sm" variant="primary" onClick={handleApplyFaults}>
                Apply Faults
              </Button>
            </div>
          </div>
        </Card>

        {/* Card 3: Reset Demo Data */}
        <div className="p-5 rounded-[8px] border border-danger/40 bg-danger-subtle/10 space-y-4 text-[13px]">
          <div>
            <h3 className="text-[16px] font-semibold text-danger">
              3. Reset Demo Data
            </h3>
            <p className="text-[12px] text-text-secondary mt-1">
              Clears all cases, runs, and events. Restores seed state. Takes &lt;5 seconds. Policy and code are not affected.
            </p>
          </div>

          <div className="space-y-2 max-w-sm">
            <Input
              label='Type "RESET" to confirm:'
              value={resetConfirmText}
              onChange={e => setResetConfirmText(e.target.value)}
              placeholder="RESET"
            />

            <Button
              variant="destructive"
              disabled={resetConfirmText.trim() !== 'RESET'}
              onClick={handleReset}
            >
              Reset
            </Button>
          </div>
        </div>

        <div className="text-center text-[12px] text-text-tertiary">
          Admin only. Role: ADMIN required.
        </div>
      </div>
    </div>
  );
};
