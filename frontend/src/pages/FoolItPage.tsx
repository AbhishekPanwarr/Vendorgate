import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { Select } from '../components/primitives/Select';
import { Dialog } from '../components/primitives/Dialog';
import { useApp } from '../context/AppContext';
import { api } from '../api';
import {
  AlertTriangle,
  Play,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface MutationOperator {
  id: string;
  name: string;
  category: string;
  description: string;
  critical: boolean;
  isControl?: boolean;
  expectedStatus: 'APPROVED' | 'PENDING' | 'REJECTED';
  expectedTier: 'LOW' | 'MEDIUM' | 'HIGH';
  reasonCode?: string;
  diffField: string;
  originalVal: string;
  mutatedVal: string;
}

export const FoolItPage: React.FC = () => {
  const { addToast } = useApp();

  const [selectedBaseVendor, setSelectedBaseVendor] = useState('HP-1');
  const [selectedOperators, setSelectedOperators] = useState<string[]>([]);
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({
    doc: true, bank: true, tax: true, name: true, san: true,
  });

  // Run execution state
  const [hasRun, setHasRun] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [attemptsCount, setAttemptsCount] = useState(0);
  const [criticalCount, setCriticalCount] = useState(0);
  const [criticalApproves, setCriticalApproves] = useState(0);

  // Run result (from POST /api/v1/foolit/run)
  const [result, setResult] = useState<null | { expected: { status: string; awaiting: string[]; blocking_reason_codes: string[]; critical: boolean }; actual: { status: string; awaiting: string[]; reason_codes: string[] }; match: boolean }>(null);
  const [operators, setOperators] = useState<MutationOperator[]>([]);

  useEffect(() => {
    let live = true;
    api.getFoolItOperators().then(list => {
      if (!live) return;
      const categoryOf = (codes: string[]) => {
        const c = codes[0] ?? '';
        if (/^NAME_/.test(c) || c === 'HOMOGLYPH_SUSPECT') return 'name';
        if (/^TAX_|^GSTIN|^PAN_|^VAT_|^TIN_/.test(c)) return 'tax';
        if (/^SAN_|^PEP_|^ADVERSE_|^EMBARGO/.test(c)) return 'san';
        if (/^MISSING_|^DOC_/.test(c)) return 'doc';
        return 'bank';
      };
      setOperators(list.map(o => {
        const exp = (o.expected ?? {}) as Record<string, unknown>;
        const codes = (exp.blocking_reason_codes ?? []) as string[];
        return {
          id: o.id, name: o.name, category: categoryOf(codes),
          description: o.description, critical: Boolean(exp.critical),
          expectedStatus: String(exp.status ?? '—') as MutationOperator['expectedStatus'],
          expectedTier: 'MEDIUM' as const, reasonCode: codes[0] ?? '',
          diffField: '', originalVal: '', mutatedVal: '',
        };
      }));
    }).catch(() => {});
    return () => { live = false; };
  }, []);

  // Free-form JSON modal
  const [isJsonModalOpen, setIsJsonModalOpen] = useState(false);
  const [customJson, setCustomJson] = useState('{\n  "vendor": "Acme Global Systems Ltd",\n  "ein": "00-9999999",\n  "bank_routing": "000000000"\n}');

  const operatorCatalog: MutationOperator[] = operators;

  const categories = [
    { id: 'doc', label: 'Document Tampering (DOC)' },
    { id: 'bank', label: 'Banking & Remittance (BNK)' },
    { id: 'tax', label: 'Tax & EIN Formats (TAX)' },
    { id: 'name', label: 'Name Fuzzy Matching (NAM)' },
    { id: 'san', label: 'Sanctions & AML (SAN)' }
  ];

  const toggleOperator = (id: string) => {
    setSelectedOperators(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleRun = async () => {
    if (selectedOperators.length === 0) return;
    setIsRunning(true);
    try {
      const r = await api.foolitRun(selectedBaseVendor, selectedOperators);
      const res = r as unknown as { expected: { status: string; awaiting: string[]; blocking_reason_codes: string[]; critical: boolean }; actual: { status: string; awaiting: string[]; reason_codes: string[] }; match: boolean };
      setResult(res);
      setHasRun(true);
      setAttemptsCount(c => c + 1);
      if (res.expected?.critical) setCriticalCount(c => c + 1);
      if (res.expected?.critical && res.actual?.status === 'APPROVED') setCriticalApproves(c => c + 1);
      addToast({
        title: res.match ? 'Mutation caught: system matched operator expectation' : 'Mismatch: system diverged from operator expectation',
        description: `Expected ${res.expected?.status}, system produced ${res.actual?.status}.`,
        variant: res.match ? 'success' : 'warning',
      });
    } catch (e) {
      addToast({ title: 'Fool-it run failed', description: e instanceof Error ? e.message : 'Server error', variant: 'danger' });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in-0 duration-240">
      <PageHeader
        title="Fool-it Lab"
        description="Attack the decision engine with document tampering, tax spoofing, and synthetic bank fraud: Adversarial Lab."
      />

      {/* Counter bar */}
      <div className="p-4 rounded-[8px] bg-surface border border-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6 text-[13px]">
          <div>
            <span className="text-text-tertiary uppercase text-[11px] block">Attempts</span>
            <span className="text-[20px] font-semibold text-text-primary tabular" data-testid="attempts">{attemptsCount}</span>
          </div>
          <div>
            <span className="text-text-tertiary uppercase text-[11px] block">Critical Mutations</span>
            <span className="text-[20px] font-semibold text-text-primary tabular">{criticalCount}</span>
          </div>
          <div>
            <span className="text-text-tertiary uppercase text-[11px] block">Critical False-Approves</span>
            <span data-testid="crit-approvals" className={`text-[20px] font-semibold tabular ${criticalApproves > 0 ? 'text-danger font-bold animate-bounce' : 'text-success'}`}>
              {criticalApproves}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsJsonModalOpen(true)}
          >
            Try free-form JSON
          </Button>
        </div>
      </div>

      {/* Main Split View: Left 40% (Operators), Right 60% (Run / Diff) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (40% = 5 cols) — Operator Picker */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between px-1">
            <span className="text-[14px] font-semibold text-text-primary">
              Mutation Operators
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-accent font-medium bg-accent-subtle/50 px-2 py-0.5 rounded">
                Selected: {selectedOperators.length}
              </span>
              {selectedOperators.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedOperators([])}
                  className="text-[11px] text-text-secondary hover:text-text-primary hover:underline"
                >
                  Clear all
                </button>
              )}
            </div>
          </div>

          <div className="space-y-3">
            {categories.map(cat => {
              const catOps = operatorCatalog.filter(o => o.category === cat.id);
              const isOpen = openCategories[cat.id] ?? false;

              return (
                <div key={cat.id} className="rounded-[8px] border border-border bg-surface overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setOpenCategories(p => ({ ...p, [cat.id]: !p[cat.id] }))}
                    className="w-full p-3 px-3.5 flex items-center justify-between hover:bg-subtle transition-colors text-left text-[13px] font-medium text-text-primary select-none"
                  >
                    <span>{cat.label}</span>
                    <span className="text-text-tertiary">
                      {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                  </button>

                  {isOpen && (
                    <div className="p-2 pt-0 space-y-1 border-t border-border-subtle bg-subtle/20 divide-y divide-border-subtle/40">
                      {catOps.map(op => {
                        const isChecked = selectedOperators.includes(op.id);
                        return (
                          <div
                            key={op.id}
                            onClick={() => toggleOperator(op.id)}
                            className="p-2.5 flex items-start gap-2.5 cursor-pointer hover:bg-surface rounded transition-colors text-[12px]"
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {}} // handled by parent div
                              className="mt-0.5 accent-accent"
                            />
                            <div className="flex-1 space-y-0.5">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-medium text-text-primary">{op.id}</span>
                                <span className="font-medium text-text-primary">{op.name}</span>
                                {op.critical && (
                                  <span title="Critical security mutation" className="shrink-0 flex items-center">
                                    <AlertTriangle size={13} className="text-accent" />
                                  </span>
                                )}
                                {op.isControl && (
                                  <Badge size="sm" color="neutral">Control</Badge>
                                )}
                              </div>
                              <p className="text-text-secondary text-[11px] leading-relaxed">
                                {op.description}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column (60% = 7 cols) — Diff Preview & Run */}
        <div className="lg:col-span-7 space-y-4">
          {/* Top: Base vendor selector */}
          <div className="p-4 rounded-[8px] bg-surface border border-border space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-semibold text-text-primary">
                Target Base Submission
              </span>
              <span className="text-[11px] text-text-tertiary font-mono">
                Clean benchmark baseline
              </span>
            </div>

            <Select
              value={selectedBaseVendor}
              onChange={setSelectedBaseVendor}
              options={[
                { value: 'HP-1', label: 'HP-1: Acme Global Systems Ltd (Clean US Corp)' },
                { value: 'HP-2', label: 'HP-2: Vertex Analytics Inc (Low Spend SaaS)' },
                { value: 'HP-3', label: 'HP-3: Beacon Cloud Infrastructure' },
                { value: 'HP-3-HIGH', label: 'HP-3-HIGH: Hyperion Logistics GmbH ($125k Spend)' },
                { value: 'EC-1', label: 'EC-1: Three Spellings, One Company' },
                { value: 'EC-3a', label: 'EC-3a: Shared Bank Account Takeover' },
                { value: 'EC-3b', label: 'EC-3b: Bank Change with Callback' },
                { value: 'EC-4a', label: 'EC-4a: Sanctions Decoy (Clears)' },
                { value: 'EC-4b', label: 'EC-4b: Sanctioned Entity (Rejects)' }
              ]}
            />
          </div>

          {/* Diff Preview */}
          <div className="rounded-[8px] border border-border bg-surface overflow-hidden">
            <div className="p-3 px-4 border-b border-border-subtle bg-canvas flex items-center justify-between text-[12px]">
              <span className="font-medium text-text-primary">Payload Mutation Diff</span>
              <span className="text-[11px] text-text-tertiary">
                {selectedOperators.length} active mutations
              </span>
            </div>

            {selectedOperators.length === 0 ? (
              <div className="p-12 text-center space-y-2">
                <h4 className="text-[20px] font-semibold text-text-primary">Try to break it.</h4>
                <p className="text-[13px] text-text-secondary max-w-sm mx-auto">
                  Pick a base vendor and toggle mutation operators to see if the pipeline catches the fault. Critical false-approves should stay at zero.
                </p>
              </div>
            ) : (
              <div className="p-4 font-mono text-[12px] space-y-2 bg-subtle/30 overflow-x-auto">
                {selectedOperators.map(opId => {
                  const op = operatorCatalog.find(o => o.id === opId);
                  if (!op) return null;
                  return (
                    <div key={op.id} className="p-2.5 rounded bg-surface border border-border-subtle space-y-1">
                      <div className="text-[11px] text-text-tertiary font-semibold uppercase">{op.id}: {op.name}</div>
                      <div className="flex flex-col gap-0.5">
                        <div className="text-danger flex items-center gap-1">
                          <span className="select-none text-text-tertiary">-</span>
                          <span>{op.diffField}: <del className="bg-danger-subtle px-1 rounded">{op.originalVal}</del></span>
                        </div>
                        <div className="text-success flex items-center gap-1">
                          <span className="select-none text-text-tertiary">+</span>
                          <span>{op.diffField}: <ins className="bg-success-subtle px-1 rounded font-bold no-underline">{op.mutatedVal}</ins></span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Run Button */}
          {selectedOperators.length > 0 && (
            <Button
              size="lg"
              variant="primary"
              className="w-full h-11 text-[14px]"
              loading={isRunning}
              data-testid="run"
              onClick={handleRun}
            >
              Run with {selectedOperators.length} mutation{selectedOperators.length > 1 ? 's' : ''}
            </Button>
          )}

          {/* After Run: Side-by-side Expected vs Actual Card */}
          {hasRun && result && selectedOperators.length > 0 && (
            <div className="p-5 rounded-[8px] bg-surface border border-border space-y-4 animate-in fade-in-0 duration-180" data-testid="result">
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <span className="text-[14px] font-semibold text-text-primary">
                  Adjudication Result Match
                </span>
                <Badge size="md" color={result.match ? 'success' : 'danger'}>
                  {result.match ? '✓ Match' : '✗ Mismatch'} · expected {result.expected.status}, system did {result.actual.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4 text-[13px]">
                {/* Expected */}
                <div className="p-3 rounded bg-subtle/40 border border-border-subtle space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-text-tertiary block">
                    Operator says the system should
                  </span>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-text-secondary text-[12px]">Status:</span>
                      <Badge variant="status" status={result.expected.status} size="sm" />
                    </div>
                    <div className="text-[11px] text-text-tertiary pt-1">
                      Reason: <span className="font-mono text-text-secondary">{(result.expected.blocking_reason_codes ?? []).join(', ') || '—'}</span>
                    </div>
                  </div>
                </div>

                {/* Actual */}
                <div className="p-3 rounded bg-subtle/40 border border-border-subtle space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-text-tertiary block">
                    System did
                  </span>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-text-secondary text-[12px]">Status:</span>
                      <Badge variant="status" status={result.actual.status} size="sm" />
                    </div>
                    <div className="text-[11px] text-text-tertiary pt-1">
                      Reason: <span className="font-mono text-text-secondary">{(result.actual.reason_codes ?? []).join(', ') || '—'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Free-form JSON Editor Modal */}
      <Dialog
        isOpen={isJsonModalOpen}
        onClose={() => setIsJsonModalOpen(false)}
        title="Custom Adversarial Payload Editor"
        description="Inject raw JSON payloads directly into the 13-stage decision engine."
        primaryAction={{
          label: 'Run Custom Payload',
          onClick: () => {
            setIsJsonModalOpen(false);
            handleRun();
          }
        }}
      >
        <div className="space-y-2">
          <textarea
            rows={8}
            value={customJson}
            onChange={e => setCustomJson(e.target.value)}
            className="w-full font-mono text-[12px] p-3 rounded-[6px] border border-border bg-subtle text-text-primary focus-ring"
          />
        </div>
      </Dialog>
    </div>
  );
};
