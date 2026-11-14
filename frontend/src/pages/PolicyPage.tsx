import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { useApp } from '../context/AppContext';
import { api } from '../api';
import { Copy, Check, ShieldCheck, Lock, ExternalLink } from 'lucide-react';

export const PolicyPage: React.FC = () => {
  const { addToast } = useApp();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [assumptions, setAssumptions] = useState<{ id: string; text: string }[]>([]);
  const [policyHash, setPolicyHash] = useState('');

  useEffect(() => {
    let live = true;
    api.getPolicy().then(p => {
      if (!live) return;
      setAssumptions(p.assumptions ?? []);
      setPolicyHash(p.policy_hash ?? '');
    }).catch(() => { if (live) addToast({ title: 'Policy unavailable', description: 'Server unreachable.', variant: 'danger' }); });
    return () => { live = false; };
  }, [addToast]);

  const copyVal = (val: string, label: string) => {
    navigator.clipboard.writeText(val);
    setCopiedKey(label);
    addToast({ title: `Copied ${label}: ${val}`, variant: 'default' });
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const versionHistory = [{ version: 'active', date: 'current', changes: 'Committed policy (policy/base.yaml)', hash: policyHash }];



  return (
    <div className="space-y-8 animate-in fade-in-0 duration-240">
      <PageHeader
        title="Policy Specifications"
        description="Formal baseline assumptions, quantitative scoring weights, and cryptographic version hashes."
      />

      {/* Notice */}
      <div className="p-3.5 rounded-[8px] bg-subtle/60 border border-border flex items-center justify-between text-[12px] text-text-secondary">
        <div className="flex items-center gap-2">
          <Lock size={14} className="text-accent" />
          <span>Policy parameters are read-only in UI. Edits occur in <code className="font-mono text-text-primary">policy/*.yaml</code>; modifications generate a new policy hash.</span>
        </div>
        <span className="font-mono text-text-primary font-medium" data-testid="policy-hash">Active Hash: {policyHash ? policyHash.slice(0, 12) : '…'}</span>
      </div>

      {/* Two Column Grid: Left 40% (Assumptions), Right 60% (Thresholds) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (40% = 5 cols) — Assumptions */}
        <div className="lg:col-span-5 space-y-6 sticky top-20 max-h-[80vh] overflow-y-auto pr-2">
          <div className="border-b border-border-subtle pb-2">
            <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
              Architectural Assumptions (A-01..A-15)
            </h3>
            <p className="text-[12px] text-text-secondary mt-0.5">
              Governing principles for automated adjudication.
            </p>
          </div>

          <div className="space-y-3" data-testid="assumptions">
            {assumptions.map(item => (
              <div key={item.id} className="p-3 rounded-[6px] bg-surface border border-border text-[13px] space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-text-tertiary font-semibold">
                    {item.id}
                  </span>
                </div>
                <p className="text-text-secondary text-[12px] leading-relaxed">
                  {item.text}
                </p>
              </div>
            ))}
            {assumptions.length === 0 && (
              <p className="text-[12px] text-text-tertiary">Loading assumptions…</p>
            )}
          </div>
        </div>
        <div className="lg:col-span-7 space-y-6">
          <div className="border-b border-border-subtle pb-2">
            <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
              Quantitative Thresholds
            </h3>
            <p className="text-[12px] text-text-secondary mt-0.5">
              Exact numerical gates driving the decision engine.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card 1: Scoring Weights */}
            <Card padding="compact" title="Component Weights">
              <div className="space-y-2 pt-2 text-[12px]">
                {[
                  { name: 'Banking & Remit', weight: '25 points' },
                  { name: 'Entity & Registry', weight: '20 points' },
                  { name: 'Sanctions & AML', weight: '20 points' },
                  { name: 'Tax Compliance', weight: '15 points' },
                  { name: 'Document Proof', weight: '10 points' },
                  { name: 'Dedupe & Graph', weight: '10 points' }
                ].map(w => (
                  <div key={w.name} className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                    <span className="text-text-primary">{w.name}</span>
                    <span className="font-mono tabular text-text-secondary">{w.weight}</span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Card 2: Tier Bands */}
            <Card padding="compact" title="Tier Classification Bands">
              <div className="space-y-2 pt-2 text-[12px]">
                {[
                  { name: 'Low Risk', range: 'Score < 40.0', badge: 'LOW' },
                  { name: 'Medium Risk', range: 'Score 40.0 – 74.9', badge: 'MEDIUM' },
                  { name: 'High Risk', range: 'Score ≥ 75.0', badge: 'HIGH' },
                  { name: 'Blocked', range: 'Sanctions violation', badge: 'BLOCKED' }
                ].map(t => (
                  <div key={t.name} className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                    <span className="text-text-primary">{t.name}</span>
                    <span className="font-mono text-text-secondary tabular">{t.range}</span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Card 3: Auto-approve Gate */}
            <Card padding="compact" title="Auto-Approve Gate">
              <div className="space-y-2 pt-2 text-[12px]">
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Max score</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>≤ 25.0</span>
                    <button type="button" onClick={() => copyVal('25.0', 'Max score')} className="hover:text-accent">
                      {copiedKey === 'Max score' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Blocking items allowed</span>
                  <span className="font-mono text-text-primary font-semibold">0</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-text-primary">Sanctions contradictions</span>
                  <span className="font-mono text-text-primary font-semibold">0</span>
                </div>
              </div>
            </Card>

            {/* Card 4: Name Matching */}
            <Card padding="compact" title="Name Matching Parameters">
              <div className="space-y-2 pt-2 text-[12px]">
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">High threshold (t_hi)</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>0.93</span>
                    <button type="button" onClick={() => copyVal('0.93', 't_hi')} className="hover:text-accent">
                      {copiedKey === 't_hi' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Low threshold (t_lo)</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>0.78</span>
                    <button type="button" onClick={() => copyVal('0.78', 't_lo')} className="hover:text-accent">
                      {copiedKey === 't_lo' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-text-primary">Subset cap</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>0.88</span>
                    <button type="button" onClick={() => copyVal('0.88', 'subset_cap')} className="hover:text-accent">
                      {copiedKey === 'subset_cap' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
              </div>
            </Card>

            {/* Card 5: Sanctions Ladder */}
            <Card padding="compact" title="Sanctions Ladder">
              <div className="space-y-2 pt-2 text-[12px]">
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Confirm threshold</span>
                  <span className="font-mono text-text-primary">0.97</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Potential threshold</span>
                  <span className="font-mono text-text-primary">0.85</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-text-primary">Min contradictions</span>
                  <span className="font-mono text-text-primary">2</span>
                </div>
              </div>
            </Card>

            {/* Card 6: Deduplication & Lifecycle */}
            <Card padding="compact" title="Dedupe & Lifecycle">
              <div className="space-y-2 pt-2 text-[12px]">
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Review threshold</span>
                  <span className="font-mono text-text-primary">0.90</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/50">
                  <span className="text-text-primary">Vendor response SLA</span>
                  <span className="font-mono text-text-primary">14 days</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-text-primary">Automated nudges</span>
                  <span className="font-mono text-text-primary">Days 1, 3, 7, 10</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Policy Version History Table */}
          <div className="space-y-3 pt-4">
            <h4 className="text-[16px] font-semibold text-text-primary tracking-tight">
              Policy Version History
            </h4>

            <div className="rounded-[8px] border border-border bg-surface overflow-hidden">
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="h-9 bg-canvas border-b border-border-subtle text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
                    <th className="px-4">Version</th>
                    <th className="px-4">Date</th>
                    <th className="px-4">Changes</th>
                    <th className="px-4 text-right">Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {versionHistory.map(row => (
                    <tr key={row.version} className="h-10 hover:bg-subtle transition-colors">
                      <td className="px-4 font-semibold text-text-primary">{row.version}</td>
                      <td className="px-4 font-mono text-text-tertiary tabular">{row.date}</td>
                      <td className="px-4 text-text-secondary truncate max-w-xs">{row.changes}</td>
                      <td className="px-4 text-right font-mono text-accent">
                        <span className="cursor-pointer hover:underline" onClick={() => copyVal(row.hash, row.version)}>
                          {row.hash}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
