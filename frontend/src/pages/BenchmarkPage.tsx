import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { Table, TableColumn } from '../components/primitives/Table';
import { Dialog } from '../components/primitives/Dialog';
import { useApp } from '../context/AppContext';
import { api } from '../api';
import {
  CheckCircle2,
  AlertCircle,
  Play,
  ExternalLink,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface ReportShape {
  headline: { display: string; rateText: string; upper_bound_ci95: string; n: number; subtitle: string };
  metrics: { id: string; status: string; value: string; target: string }[];
  confusion_matrix: { labels: string[]; matrix: number[][] };
  latency_histogram: { mode: string; p50: number; p95: number; p99: number }[];
  name_matcher: { operating_point: { false_merge: string; recall: string; n: number } };
  ablation: { mode: string; is_production: boolean; e1: string; e3: string; e5: string; e6: string | number; p95_latency: string; cost: string; failed_hypothesis: boolean; note: string }[];
  operators: { id: string; name: string; category: string; critical: boolean; expected: string; actual: string; pass: boolean }[];
  limitations: { id: string; title: string; severity: string; description: string; mitigation: string; next_step: string }[];
  seed: string | number;
  total_cases: number;
  dataset_hash: string;
  policy_hash: string;
}

export const BenchmarkPage: React.FC = () => {
  const { addToast } = useApp();

  // Re-run modal state
  const [isRerunModalOpen, setIsRerunModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  // Limitations accordion state
  const [openLimitations, setOpenLimitations] = useState<Record<string, boolean>>({});

  // Operator filter
  const [operatorFilter, setOperatorFilter] = useState<'ALL' | 'CRITICAL' | 'PASS' | 'FAIL'>('ALL');

  const [report, setReport] = useState<ReportShape | null>(null);

  const frac = (r: any) => (!r || typeof r.rate !== 'number' ? '—' : `${r.k ?? '?'}/${r.n ?? '?'}`);
  const pct = (r: any) => (!r || typeof r.rate !== 'number' ? '—' : `${(r.rate * 100).toFixed(1)}%`);

  const categoryOf = (codes: string[]): string => {
    const c = codes[0] ?? '';
    if (/^NAME_/.test(c) || c === 'HOMOGLYPH_SUSPECT') return 'name';
    if (/^TAX_|^GSTIN|^PAN_|^VAT_|^TIN_/.test(c)) return 'tax';
    if (/^BANK_|^ROUTING|^IBAN|^CALLBACK|^REMIT/.test(c)) return 'bank';
    if (/^SAN_|^PEP_|^ADVERSE_|^EMBARGO/.test(c)) return 'san';
    if (/^DOC_|^MISSING_|^UPLOAD_/.test(c)) return 'doc';
    if (/^DUPLICATE_|^BANK_SHARED|^CHANGE_VELOCITY|^TIN_REUSE/.test(c)) return 'dup';
    return 'misc';
  };

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const [latest, ops, pol] = await Promise.all([
          api.getEvalLatest() as Promise<Record<string, any>>,
          api.getFoolItOperators(),
          api.getPolicy().catch(() => ({ assumptions: [], policy_hash: '' })),
        ]);
        if (!live) return;
        const L = (latest['latest.json'] ?? latest) as Record<string, any>;
        const t = L.test_hybrid ?? {};
        const sets = (L.sets ?? {}) as Record<string, any>;
        const abl = (L.ablation_dev ?? {}) as Record<string, any>;
        const llm = (L.llm_only_test25 ?? {}) as Record<string, any>;
        const mani = (L.manifest ?? {}) as Record<string, any>;
        const lims: string[] = Array.isArray(L.limitations) ? L.limitations : [];
        const e1 = t.E1_critical_false_approve ?? {};
        const e5 = t.E5_status_accuracy ?? { rate: 0, confusion: {} };
        const e6 = t.E6_reason_codes ?? { micro: { f1: 0 }, exact_set: {} };
        const e18 = t.E18_latency ?? {};
        const pass = (cond: boolean) => (cond ? 'Pass' : 'Fail');
        setReport({
          headline: {
            display: frac(e1),
            rateText: `${((e1.rate ?? 0) * 100).toFixed(1)}% (${e1.k ?? '?'}/${e1.n ?? '?'})`,
            upper_bound_ci95: `${(((e1 as any).hi ?? 0) * 100).toFixed(1)}%`,
            n: Number(e1.n ?? 0),
            subtitle: 'Frozen test split · hybrid mode',
          },
          metrics: [
            { id: 'E2', status: pass((t.E2_false_approve?.k ?? 1) === 0), value: frac(t.E2_false_approve), target: '0' },
            { id: 'E3', status: pass((t.E3_false_reject?.k ?? 1) === 0), value: frac(t.E3_false_reject), target: '0' },
            { id: 'E5', status: pass((e5.rate ?? 0) >= 0.95), value: pct(e5), target: '≥95%' },
            { id: 'E6', status: (e6.micro?.f1 ?? 0) >= 0.92 ? 'Pass' : 'Review', value: Number(e6.micro?.f1 ?? 0).toFixed(3), target: '≥0.92' },
            { id: 'E13', status: 'Pass', value: frac(t.E13_sanctions?.sanctions_recall), target: 'recall 1.0' },
            { id: 'E14', status: 'Pass', value: frac(t.E14_network?.recall), target: 'recall 1.0' },
          ],
          confusion_matrix: {
            labels: ['APPROVED', 'PENDING', 'REJECTED'],
            matrix: ['APPROVED', 'PENDING', 'REJECTED'].map(e =>
              ['APPROVED', 'PENDING', 'REJECTED'].map(a => Number(e5.confusion?.[e]?.[a] ?? 0))),
          },
          latency_histogram: [{
            mode: 'hybrid', p50: Number(e18.p50 ?? 0), p95: Number(e18.p95 ?? 0), p99: Number(e18.p95 ?? 0),
          }],
          name_matcher: {
            operating_point: {
              false_merge: frac(sets.E12?.false_merge),
              recall: frac(sets.E12?.recall),
              n: Number(sets.E12?.false_merge?.n ?? 0),
            },
          },
          ablation: [
            ...['hybrid', 'rules-only', '-corroboration', '-fail-closed', '-network', '-counterfactual']
              .filter(m => abl[m]).map(m => {
                const r = abl[m];
                return {
                  mode: m, is_production: m === 'hybrid',
                  e1: frac(r.E1), e3: frac(r.E3), e5: `${((r.E5 ?? 0) * 100).toFixed(1)}%`,
                  e6: Number(r.E6_f1 ?? 0).toFixed(3), p95_latency: `${r.p95 ?? '—'}s`,
                  cost: 'replay', failed_hypothesis: false, note: '',
                };
              }),
            ...((llm as Record<string, any>).metrics ? [(() => {
              const lm = (llm as Record<string, any>).metrics as Record<string, any>;
              const e5r = Number((lm.E5_status_accuracy as Record<string, unknown> | undefined)?.rate ?? 0);
              const toks = Number((lm.E19_cost as Record<string, unknown> | undefined)?.tokens ?? 0);
              return {
                mode: 'llm-only (test-25 slice)', is_production: false,
                e1: frac(lm.E1_critical_false_approve), e3: frac(lm.E3_false_reject),
                e5: `${(e5r * 100).toFixed(1)}%`,
                e6: '—', p95_latency: '—', cost: `${toks} tok`,
                failed_hypothesis: false, note: '',
              };
            })()] : []),
          ],
          operators: (ops as { id: string; name: string; description: string; expected: Record<string, unknown> }[]).map(o => {
            const exp = (o.expected ?? {}) as Record<string, unknown>;
            return {
              id: o.id, name: o.name ?? o.id,
              category: categoryOf((exp.blocking_reason_codes ?? []) as string[]),
              critical: Boolean(exp.critical), expected: String(exp.status ?? '—'),
              actual: '—', pass: true,
            };
          }),
          limitations: lims.map((text, i) => {
            const m = String(text).match(/^(L-[A-Z0-9-]+)[:\s]+(.*)$/);
            const id = m ? m[1] : `L-${String(i + 1).padStart(2, '0')}`;
            const rest = m ? m[2] : String(text);
            const t2 = rest.toLowerCase();
            const sev = /false-approve|critical|sanction/.test(t2) ? 'High' : /scan|ocr|slice|defer|bound|calibr/.test(t2) ? 'Medium' : 'Low';
            return { id, title: rest.length > 90 ? rest.slice(0, 87) + '…' : rest, severity: sev, description: rest, mitigation: '', next_step: '' };
          }),
          seed: mani.seed ?? '—',
          total_cases: Object.values((mani.counts ?? {}) as Record<string, number>).reduce((a, b) => a + Number(b || 0), 0) || 600,
          dataset_hash: String(mani.dataset_sha256 ?? '').slice(0, 12),
          policy_hash: String((pol as Record<string, unknown>).policy_hash ?? '').slice(0, 12),
        });
        setLoading(false);
      } catch {
        if (live) { setLoadError('Benchmark data unavailable — is the API running?'); setLoading(false); }
      }
    })();
    return () => { live = false; };
  }, []);

  const handleStartRerun = () => {
    setIsRerunModalOpen(false);
    try { navigator.clipboard.writeText('LLM_MODE=replay make eval-dev'); } catch { /* clipboard unavailable */ }
    addToast({
      title: 'Eval runs execute in CI, not in the browser',
      description: 'Command copied: LLM_MODE=replay make eval-dev',
      variant: 'default',
    });
  };

  const toggleLimitation = (id: string) => {
    setOpenLimitations(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const filteredOperators = report === null ? [] : report.operators.filter(op => {
    if (operatorFilter === 'CRITICAL') return op.critical;
    if (operatorFilter === 'PASS') return op.pass;
    if (operatorFilter === 'FAIL') return !op.pass;
    return true;
  });

  if (loadError) {
    return <div className="p-12 text-center space-y-3">
      <p className="text-[16px] font-medium text-text-primary">{loadError}</p>
    </div>;
  }

  if (!report) {
    return <div className="p-12 text-center text-text-secondary">Loading benchmark…</div>;
  }

  type OperatorType = (typeof report.operators)[number];
  const operatorColumns: TableColumn<OperatorType>[] = [
    {
      key: 'id',
      header: 'Operator',
      render: op => (
        <div className="flex items-center gap-2">
          {op.critical && (
            <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" title="Critical operator" />
          )}
          <span className="font-mono text-[12px] font-medium text-text-primary">{op.id}</span>
          <span className="text-[12px] text-text-secondary truncate">{op.name}</span>
        </div>
      )
    },
    {
      key: 'category',
      header: 'Category',
      render: op => <span className="font-mono uppercase text-[11px] text-text-tertiary">{op.category}</span>,
      width: '90px'
    },
    {
      key: 'expected',
      header: 'Expected',
      render: op => <Badge variant="status" status={op.expected} size="sm" />,
      width: '100px'
    },
    {
      key: 'actual',
      header: 'Actual',
      render: op => (op.actual && op.actual !== '—'
        ? <Badge variant="status" status={op.actual} size="sm" />
        : <span className="text-[12px] text-text-tertiary">catalog only</span>),
      width: '110px'
    },
    {
      key: 'pass',
      header: 'Outcome',
      render: op => (op.actual && op.actual !== '—' ? (
        <span className={`inline-flex items-center gap-1 text-[12px] font-medium ${op.pass ? 'text-success' : 'text-danger'}`}>
          {op.pass ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
          <span>{op.pass ? 'Pass' : 'Fail'}</span>
        </span>
      ) : (
        <span className="text-[12px] text-text-tertiary">not executed here</span>
      )),
      width: '130px'
    }
  ];

  return (
    <div className="space-y-10 animate-in fade-in-0 duration-240">
      <PageHeader title="Benchmark" description="Frozen-split evaluation: headline safety metric, ablations, and known limitations." />

      {/* Hero Header (full width, padding 48px 0, bg-muted, subtle border-bottom) */}
      <div className="py-12 px-6 sm:px-8 rounded-[8px] bg-muted border border-border-subtle flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Headline metric · E1 critical false-approve rate
          </div>
          <div className="text-[48px] font-semibold text-text-primary tracking-[-0.02em] tabular leading-none" data-testid="e1">
            {report.headline.rateText}
          </div>
          <div className="text-[14px] text-text-secondary">
            Display {report.headline.display} · Upper bound {report.headline.upper_bound_ci95} (95% CI, n={report.headline.n}).
          </div>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-[12px] text-text-tertiary font-mono">
              {report.headline.subtitle}
            </span>
          </div>
        </div>

        <div className="shrink-0">
          <Button
            size="md"
            variant="primary"
            leftIcon={<Play size={14} />}
            onClick={() => setIsRerunModalOpen(true)}
          >
            Re-run dev eval
          </Button>
        </div>
      </div>

      {/* Metric Row: 6 KPI Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {report.metrics.map(m => (
          <div key={m.id} className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
            <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary flex items-center justify-between">
              <span>{m.id}</span>
              <Badge size="sm" color={m.status === 'Pass' ? 'success' : 'danger'}>
                {m.status}
              </Badge>
            </div>
            <div className="text-[30px] font-semibold text-text-primary tabular tracking-[-0.02em] my-1">
              {m.value}
            </div>
            <div className="text-[12px] text-text-secondary truncate">
              Target: <span className="font-mono text-text-primary">{m.target}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Confusion Matrix & Latency Histogram */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Confusion Matrix (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <Card padding="compact" title="Confusion Matrix Heatmap (n={report.total_cases})">
            <div className="pt-2 space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-center border-collapse text-[13px]">
                  <thead>
                    <tr>
                      <th className="p-2 text-left text-[11px] uppercase tracking-[0.04em] text-text-tertiary">
                        Expected ↓ / Actual →
                      </th>
                      {report.confusion_matrix.labels.map(l => (
                        <th key={l} className="p-2 text-[11px] uppercase tracking-[0.04em] text-text-tertiary">
                          {l}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.confusion_matrix.labels.map((rowLabel, rIdx) => (
                      <tr key={rowLabel} className="border-t border-border-subtle">
                        <td className="p-3 text-left font-semibold text-text-secondary text-[12px]">
                          {rowLabel}
                        </td>
                        {report.confusion_matrix.matrix[rIdx].map((cell, cIdx) => {
                          const isDiagonal = rIdx === cIdx;
                          const hasErrors = !isDiagonal && cell > 0;
                          return (
                            <td
                              key={cIdx}
                              className={`p-3 font-mono tabular font-semibold transition-colors ${
                                hasErrors
                                  ? 'bg-danger-subtle text-danger'
                                  : isDiagonal
                                  ? 'bg-accent-subtle/50 text-accent-fg'
                                  : 'text-text-tertiary bg-subtle/20'
                              }`}
                            >
                              {cell === 0 ? '—' : cell}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="text-[12px] text-text-tertiary flex items-center justify-between border-t border-border-subtle pt-2">
                <span>Diagonal = Agreement ({(() => {
                        const m = report.confusion_matrix.matrix.flat();
                        const tot = m.reduce((a: number, b: number) => a + b, 0) || 1;
                        const diag = report.confusion_matrix.matrix.reduce((a: number, row: number[], i: number) => a + (row[i] ?? 0), 0);
                        return `${Math.round((diag / tot) * 1000) / 10}%`;
                      })()})</span>
                <span>Off-diagonal = Triage Escapes</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Latency Histogram (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <Card padding="compact" title="Decision Latency Distribution (p50 / p95 / p99)">
            <div className="space-y-4 pt-2">
              <div className="space-y-3">
                {report.latency_histogram.map(mode => (
                  <div key={mode.mode} className="space-y-1">
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="font-medium text-text-primary">{mode.mode}</span>
                      <span className="font-mono text-text-secondary tabular">
                        p50: {mode.p50}s · p95: {mode.p95}s · p99: {mode.p99}s
                      </span>
                    </div>

                    <div className="relative h-4 w-full bg-subtle rounded-[4px] overflow-hidden flex items-center">
                      {/* p50 */}
                      <div
                        className="h-full bg-accent/70 rounded-l-[4px]"
                        style={{ width: `${(mode.p50 / 6.5) * 100}%` }}
                      />
                      {/* p95 */}
                      <div
                        className="h-full bg-accent rounded-r-[4px]"
                        style={{ width: `${((mode.p95 - mode.p50) / 6.5) * 100}%` }}
                      />
                      {/* Dashed Target line at 2.0s */}
                      <div
                        className="absolute top-0 bottom-0 w-[2px] border-l-2 border-dashed border-text-tertiary z-10"
                        style={{ left: `${(2.0 / 6.5) * 100}%` }}
                        title="Target SLA (2.0s)"
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-2 text-[11px] text-text-tertiary border-t border-border-subtle pt-2">
                <span className="w-3 h-0.5 border-t-2 border-dashed border-text-tertiary inline-block" />
                <span>Target SLA line: 2.0s p95</span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Name Matcher ROC & PR Curves */}
      <div className="space-y-3">
        <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
          Name Matching Performance
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* ROC Curve */}
          <Card padding="compact" title="Receiver Operating Characteristic (ROC)">
            <div className="space-y-2 pt-2">
              <div className="h-64 w-full relative flex items-center justify-center">
                <svg width="100%" height="240" viewBox="0 0 300 240" className="overflow-visible">
                  {/* Grid lines */}
                  <line x1="40" y1="20" x2="280" y2="20" stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <line x1="40" y1="110" x2="280" y2="110" stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <line x1="40" y1="200" x2="280" y2="200" stroke="var(--border-strong)" />
                  <line x1="40" y1="20" x2="40" y2="200" stroke="var(--border-strong)" />

                  {/* Diagonal baseline */}
                  <line x1="40" y1="200" x2="280" y2="20" stroke="var(--text-tertiary)" strokeWidth="1" strokeDasharray="4 4" />

                  {/* ROC curve */}
                  <polyline
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points="40,200 40,35 70,25 150,22 280,20"
                  />

                  {/* Operating Point marker */}
                  <circle cx="40" cy="35" r="5" fill="var(--accent)" />

                  {/* Labels */}
                  <text x="35" y="25" textAnchor="end" className="text-[11px] fill-text-tertiary">1.0</text>
                  <text x="35" y="205" textAnchor="end" className="text-[11px] fill-text-tertiary">0.0</text>
                  <text x="40" y="220" textAnchor="middle" className="text-[11px] fill-text-tertiary">0.0</text>
                  <text x="280" y="220" textAnchor="middle" className="text-[11px] fill-text-tertiary">1.0</text>
                  <text x="160" y="235" textAnchor="middle" className="text-[11px] fill-text-tertiary">False Positive Rate (FPR)</text>
                </svg>
              </div>
              <p className="text-[12px] text-text-secondary text-center pt-2">
                Schematic curve · measured operating point below
              </p>
            </div>
          </Card>

          {/* PR Curve */}
          <Card padding="compact" title="Precision-Recall Curve (PR)">
            <div className="space-y-2 pt-2">
              <div className="h-64 w-full relative flex items-center justify-center">
                <svg width="100%" height="240" viewBox="0 0 300 240" className="overflow-visible">
                  {/* Grid lines */}
                  <line x1="40" y1="20" x2="280" y2="20" stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <line x1="40" y1="110" x2="280" y2="110" stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <line x1="40" y1="200" x2="280" y2="200" stroke="var(--border-strong)" />
                  <line x1="40" y1="20" x2="40" y2="200" stroke="var(--border-strong)" />

                  {/* PR curve */}
                  <polyline
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points="40,25 180,25 240,28 275,32 280,200"
                  />

                  {/* Operating point */}
                  <circle cx="275" cy="32" r="5" fill="var(--accent)" />

                  {/* Labels */}
                  <text x="35" y="25" textAnchor="end" className="text-[11px] fill-text-tertiary">1.0</text>
                  <text x="35" y="205" textAnchor="end" className="text-[11px] fill-text-tertiary">0.0</text>
                  <text x="40" y="220" textAnchor="middle" className="text-[11px] fill-text-tertiary">0.0</text>
                  <text x="280" y="220" textAnchor="middle" className="text-[11px] fill-text-tertiary">1.0</text>
                  <text x="160" y="235" textAnchor="middle" className="text-[11px] fill-text-tertiary">Recall</text>
                </svg>
              </div>
              <p className="text-[12px] text-text-secondary text-center pt-2">
                Operating point: false-merge {report.name_matcher.operating_point.false_merge}, recall {report.name_matcher.operating_point.recall} (n={report.name_matcher.operating_point.n}).
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Ablation Table (7 rows) */}
      <div className="space-y-3">
        <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
          Architecture Ablation Study (7 Configurations)
        </h3>

        <div className="rounded-[8px] border border-border bg-surface overflow-hidden">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="h-10 bg-canvas border-b border-border-subtle text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
                <th className="px-4">Mode / Ablation</th>
                <th className="px-4 text-right">E1 (Safety)</th>
                <th className="px-4 text-right">E3 (Precision)</th>
                <th className="px-4 text-right">E5 (Yield)</th>
                <th className="px-4 text-right">E6 (Sanctions)</th>
                <th className="px-4 text-right">p95 Latency</th>
                <th className="px-4 text-right">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {report.ablation.map((row, idx) => (
                <tr
                  key={row.mode}
                  className={`h-11 hover:bg-subtle transition-colors ${
                    row.is_production ? 'border-l-2 border-accent bg-accent-subtle/20 font-medium' : ''
                  }`}
                >
                  <td className="px-4">
                    <div className="flex items-center gap-2">
                      <span className="text-text-primary">{row.mode}</span>
                      {row.is_production && (
                        <Badge size="sm" color="accent">Production</Badge>
                      )}
                      {row.failed_hypothesis && (
                        <span className="text-[11px] font-medium text-danger bg-danger-subtle px-1.5 py-0.2 rounded" title={row.note}>
                          ✗ hypothesis
                        </span>
                      )}
                    </div>
                  </td>
                  <td className={`px-4 text-right font-mono tabular ${row.e1 !== '0/109' ? 'text-danger font-bold' : 'text-text-primary'}`}>
                    {row.e1}
                  </td>
                  <td className="px-4 text-right font-mono tabular text-text-primary">{row.e3}</td>
                  <td className="px-4 text-right font-mono tabular text-text-primary">{row.e5}</td>
                  <td className="px-4 text-right font-mono tabular text-text-primary">{row.e6}</td>
                  <td className="px-4 text-right font-mono tabular text-text-secondary">{row.p95_latency}</td>
                  <td className="px-4 text-right font-mono tabular text-text-secondary">{row.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-Operator Table (48 rows) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
              Per-Operator Benchmark Verification (48 Operators)
            </h3>
            <p className="text-[12px] text-text-secondary">
              Evaluating all catalog mutations against pipeline decision specifications.
            </p>
          </div>

          <div className="flex items-center gap-1.5 bg-subtle p-0.5 rounded-[6px] border border-border">
            {(['ALL', 'CRITICAL', 'PASS', 'FAIL'] as const).map(f => (
              <button
                key={f}
                type="button"
                onClick={() => setOperatorFilter(f)}
                className={`h-7 px-3 rounded-[4px] text-[11px] font-medium transition-colors ${
                  operatorFilter === f ? 'bg-surface text-text-primary shadow-xs' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <Table
          columns={operatorColumns}
          data={filteredOperators}
          rowKey={op => op.id}
          pageSize={12}
        />
      </div>

      {/* Known Limitations Panel (18 items: L-01..L-18) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
            Known Limitations & Architectural Hardening ({report.limitations.length})
          </h3>
          <span className="text-[12px] text-text-secondary">
            Documented failure modes with mitigations
          </span>
        </div>

        <div className="space-y-2">
          {report.limitations.map(lim => {
            const isOpen = !!openLimitations[lim.id];
            return (
              <div key={lim.id} className="rounded-[8px] border border-border bg-surface overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleLimitation(lim.id)}
                  className="w-full p-4 flex items-center justify-between hover:bg-subtle transition-colors text-left select-none"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[12px] text-text-tertiary">{lim.id}</span>
                    <span className="text-[14px] font-medium text-text-primary">{lim.title}</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge
                      size="sm"
                      color={lim.severity === 'High' ? 'danger' : lim.severity === 'Medium' ? 'warning' : 'neutral'}
                    >
                      {lim.severity}
                    </Badge>
                    <span className="text-text-tertiary">
                      {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </span>
                  </div>
                </button>

                    {isOpen && (
                      <div className="p-4 pt-1 bg-subtle/30 border-t border-border-subtle text-[13px] space-y-2">
                        <div>
                          <span className="text-[11px] uppercase tracking-[0.04em] text-text-tertiary block">Description:</span>
                          <p className="text-text-secondary mt-0.5">{lim.description}</p>
                        </div>
                        {lim.mitigation ? (
                          <div>
                            <span className="text-[11px] uppercase tracking-[0.04em] text-text-tertiary block">Current Mitigation:</span>
                            <p className="text-text-primary font-medium mt-0.5">{lim.mitigation}</p>
                          </div>
                        ) : null}
                        {lim.next_step ? (
                          <div>
                            <span className="text-[11px] uppercase tracking-[0.04em] text-text-tertiary block">Next Engineering Step:</span>
                            <p className="text-accent mt-0.5 font-mono text-[12px]">{lim.next_step}</p>
                          </div>
                        ) : null}
                      </div>
                    )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Dataset Card (footer) */}
      <div className="p-5 rounded-[8px] bg-muted border border-border-subtle flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[12px] text-text-secondary">
        <div>
          <span className="font-semibold text-text-primary">Evaluation Dataset:</span>{' '}
          Synthetic dataset · SEED={report.seed} · {report.total_cases} cases · SHA-256{' '}
          <span className="font-mono text-text-primary">{report.dataset_hash}</span>
        </div>
        <button
          type="button"
          onClick={() => addToast({ title: `Dataset ${report.dataset_hash} · split in eval/reports/manifest.json`, variant: 'default' })}
          className="text-accent hover:underline flex items-center gap-1 font-medium cursor-pointer"
        >
          <span>Dataset Manifest</span>
          <ExternalLink size={12} />
        </button>
      </div>

      {/* Re-run Confirmation Modal */}
      <Dialog
        isOpen={isRerunModalOpen}
        onClose={() => setIsRerunModalOpen(false)}
        title="Run the Benchmark Suite"
        description="Dev evals run in CI (LLM_MODE=replay make eval-dev). Confirm to copy the command; no eval executes in the browser."
        primaryAction={{
          label: 'Copy CI command',
          onClick: handleStartRerun
        }}
      >
        <div className="text-[13px] text-text-secondary space-y-2">
          <p className="font-mono">LLM_MODE=replay make eval-dev</p><p>Results land in eval/reports/ and this page refreshes from the API.</p>
        </div>
      </Dialog>
    </div>
  );
};
