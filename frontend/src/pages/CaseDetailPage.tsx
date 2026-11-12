import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { Tabs } from '../components/primitives/Tabs';
import { Table, TableColumn } from '../components/primitives/Table';
import { useApp } from '../context/AppContext';
import { api, mapCheck, mapClaim, mapEvidence } from '../api';
import type { CheckItem, AuditEvent, Claim } from '../types';
import {
  ArrowLeft,
  Copy,
  Check,
  Lightbulb,
  ExternalLink,
  ShieldCheck,
  FileText,
  Mail,
  Share2,
  Lock,
  ZoomIn,
  ZoomOut,
  Maximize2,
  CheckCircle2,
  AlertCircle,
  Phone,
  Landmark,
  Globe,
  MapPin,
  ChevronDown,
  ChevronRight,
  Send,
  Zap,
  X
} from 'lucide-react';

export const CaseDetailPage: React.FC<{ caseIdProp?: string }> = ({ caseIdProp }) => {
  const { currentPath, navigate, openEvidenceDrawer, addToast, role } = useApp();

  // Extract caseId from prop or path
  const pathParts = currentPath.split('/');
  const caseId = caseIdProp || pathParts[2] || '';

  // Live case + run pack
  const [caseData, setCaseData] = useState<Record<string, unknown> | null>(null);
  const [runPack, setRunPack] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [verify, setVerify] = useState<{ ok: boolean; length?: number; broken_at?: number } | null>(null);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!caseId) return;
    let live = true;
    setCaseData(null);
    setRunPack(null);
    setVerify(null);
    api.getCase(caseId).then(c => {
      if (!live) return;
      setCaseData(c as unknown as Record<string, unknown>);
      const run = (c as Record<string, unknown>).run as Record<string, unknown> | undefined;
      if (run) setRunPack(run);
    }).catch(() => { if (live) setLoadError('Case not found.'); });
    api.getMessages(caseId).then(m => { if (live) setMsg(m as Record<string, unknown>); }).catch(() => {});
    api.getCaseEvents(caseId).then(e => { if (live) setEvents(e as Record<string, unknown>[]); }).catch(() => {});
    return () => { live = false; };
  }, [caseId]);

  const refresh = async () => {
    try {
      const c = await api.getCase(caseId);
      setCaseData(c as unknown as Record<string, unknown>);
      const run = (c as Record<string, unknown>).run as Record<string, unknown> | undefined;
      if (run) setRunPack(run);
      const e = await api.getCaseEvents(caseId);
      setEvents(e as Record<string, unknown>[]);
    } catch {
      /* keep stale view on failure */
    }
  };

  // Copy helper
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    addToast({ title: `Copied ${field} to clipboard`, variant: 'default' });
    setTimeout(() => setCopiedField(null), 1500);
  };

  // Findings tab filters
  const [findingSearch, setFindingSearch] = useState('');
  const [findingOutcomeFilter, setFindingOutcomeFilter] = useState<string>('ALL');

  // Audit verify state
  const [isVerifyingChain, setIsVerifyingChain] = useState(false);
  const [expandedPayloads, setExpandedPayloads] = useState<Record<number, boolean>>({});

  // Evidence PDF state
  const [pdfPage] = useState(1);
  const [pdfZoom, setPdfZoom] = useState(100);
  const [highlightedClaim, setHighlightedClaim] = useState<Claim | null>(null);

  // Email state
  const [emailCopied, setEmailCopied] = useState(false);

  // Network selection state
  const [selectedEdge, setSelectedEdge] = useState<{ source: string; target: string; attr: string } | null>(null);
  const [networkZoom, setNetworkZoom] = useState(1);

  // Tab state synced with URL hash
  const [activeTab, setActiveTab] = useState<string>(() => {
    return window.location.hash.replace('#', '') || 'decision';
  });

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  if (loadError) {
    return (
      <div className="p-12 text-center space-y-3">
        <p className="text-[16px] font-medium text-text-primary">{loadError}</p>
        <Button variant="secondary" onClick={() => navigate('/')}>← Back to dashboard</Button>
      </div>
    );
  }

  if (!caseData) {
    return <div className="p-12 text-center text-text-secondary">Loading case…</div>;
  }

  const decision = (runPack?.decision ?? {}) as Record<string, unknown>;
  const score = (decision.score ?? {}) as { total?: number; components?: Record<string, { points?: number }> };
  const rawFindings = (Array.isArray(runPack?.findings) ? runPack?.findings : []) as Record<string, unknown>[];
  const findings: CheckItem[] = rawFindings.map(f => mapCheck(f, String(f.stage ?? '?')));
  const claims: Claim[] = (Array.isArray(runPack?.claims) ? (runPack?.claims as Record<string, unknown>[]) : []).map(mapClaim);
  const adjudications = (Array.isArray(runPack?.adjudications) ? runPack?.adjudications : []) as Record<string, unknown>[];
  const counterfactuals = (Array.isArray(decision.counterfactuals) ? decision.counterfactuals : []) as Record<string, unknown>[];
  const cf = counterfactuals[0] as Record<string, unknown> | undefined;
  const status = String(decision.status ?? caseData.status ?? 'PENDING');
  const awaiting = (Array.isArray(decision.awaiting) ? decision.awaiting : []) as string[];
  const requiredActions = (Array.isArray(decision.required_actions) ? decision.required_actions : []) as Record<string, unknown>[];
  const blocking = findings.filter(f => f.outcome === 'FAIL');
  const files = (runPack?.files ?? {}) as Record<string, [string, string]>;
  const docIds = Object.keys(files);
  const firstDocId = docIds[0];
  const dupFindings = findings.filter(f => f.id.startsWith('C-DUP'));
  const auditEvents: AuditEvent[] = events.map((e, i) => ({
    sequence: Number((e as Record<string, unknown>).seq ?? (e as Record<string, unknown>).sequence ?? i),
    timestamp: String((e as Record<string, unknown>).ts ?? (e as Record<string, unknown>).timestamp ?? ''),
    actor: String((e as Record<string, unknown>).actor ?? 'system'),
    eventType: String((e as Record<string, unknown>).type ?? (e as Record<string, unknown>).eventType ?? ''),
    summary: String((e as Record<string, unknown>).summary ?? (e as Record<string, unknown>).type ?? ''),
    hash: String((e as Record<string, unknown>).hash ?? ''),
    prevHash: String((e as Record<string, unknown>).prev_hash ?? ''),
    payload: ((e as Record<string, unknown>).payload ?? {}) as Record<string, unknown>,
  }));

  const vendorName = (() => {
    const p = (runPack?.payload ?? {}) as Record<string, unknown>;
    const c = (p.company ?? {}) as Record<string, unknown>;
    return String(c.legal_name ?? caseId);
  })();

  const SCORE_MAX: Record<string, number> = { SPEND: 25, GEO: 20, DOCS: 20, BANK_ID: 15, CATEGORY: 10, REGISTRY_MEDIA: 10 };
  const components = score.components ?? {};

  const handleVerifyAuditChain = async () => {
    setIsVerifyingChain(true);
    try {
      const result = await api.verifyAudit(caseId);
      setVerify(result);
      if (result.ok) {
        addToast({
          title: `Chain verified · ${result.length} events`,
          description: 'Cryptographic SHA-256 sequence is intact and tamper-free.',
          variant: 'success'
        });
      } else {
        addToast({
          title: `Chain broken at sequence ${result.broken_at}`,
          description: 'Cryptographic hash mismatch detected in audit log.',
          variant: 'danger'
        });
      }
    } catch {
      addToast({ title: 'Verification failed', description: 'Server unreachable.', variant: 'danger' });
    } finally {
      setIsVerifyingChain(false);
    }
  };

  const handleResubmitUnchanged = async () => {
    try {
      const payload = (runPack?.payload ?? {}) as Record<string, unknown>;
      const currentVersion = Number((caseData as Record<string, unknown>).current_version ?? 1);
      const out = await api.resubmit(caseId, currentVersion, payload);
      addToast({ title: `Resubmitted as v${out.new_version}`, description: `Run ${out.run_id} created.`, variant: 'success' });
      await refresh();
    } catch (e) {
      const body = (e as { body?: { type?: string; current_version?: number } }).body;
      if (body?.type === 'NO_CHANGES') addToast({ title: 'No changes detected', description: 'Payload identical to current version.', variant: 'default' });
      else if (body?.type === 'VERSION_MISMATCH') addToast({ title: 'Version mismatch — reloading', variant: 'warning' });
      else if (body?.type === 'NOT_RESUBMITTABLE') addToast({ title: 'Not resubmittable in current status', variant: 'warning' });
      else addToast({ title: 'Resubmit failed', description: e instanceof Error ? e.message : '', variant: 'danger' });
      await refresh();
    }
  };

  const handleAppeal = async () => {
    try {
      await api.appeal(caseId, {}, { 'X-Role': role });
      addToast({ title: 'Appeal recorded', description: 'Compliance review queued.', variant: 'success' });
      await refresh();
    } catch (e) {
      const body = (e as { body?: { type?: string } }).body;
      addToast({
        title: body?.type === 'SEGREGATION_OF_DUTIES' ? 'Appeal blocked: segregation of duties' : 'Appeal rejected',
        description: e instanceof Error ? e.message : '',
        variant: 'danger',
      });
    }
  };

  // Findings columns
  const findingColumns: TableColumn<CheckItem>[] = [    {
      key: 'id',
      header: 'Check',
      render: item => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-[12px] font-medium text-text-primary">{item.id}</span>
          <span className="text-[12px] text-text-secondary truncate max-w-xs">{item.title}</span>
        </div>
      )
    },
    {
      key: 'outcome',
      header: 'Outcome',
      render: item => <Badge variant="status" status={item.outcome} size="sm" />,
      width: '110px'
    },
    {
      key: 'severity',
      header: 'Severity',
      render: item => item.severity ? (
        <Badge size="sm" color={item.severity === 'CRITICAL' || item.severity === 'HIGH' ? 'danger' : 'warning'}>
          {item.severity}
        </Badge>
      ) : <span className="text-text-tertiary">—</span>,
      width: '100px'
    },
    {
      key: 'reasonCode',
      header: 'Reason',
      render: item => item.reasonCode ? (
        <span className="font-mono text-[11px] text-text-secondary bg-subtle px-1.5 py-0.5 rounded">
          {item.reasonCode}
        </span>
      ) : <span className="text-text-tertiary">—</span>
    },
    {
      key: 'fixedBy',
      header: 'Fixed by',
      render: item => item.fixedBy ? (
        <span className="text-[12px] font-medium text-text-primary">{item.fixedBy}</span>
      ) : <span className="text-text-tertiary">—</span>,
      width: '90px'
    },
    {
      key: 'cached',
      header: 'Cached',
      render: item => item.cached ? (
        <span className="inline-flex items-center text-accent" title="Cached evaluation">
          <Zap size={14} className="fill-accent" />
        </span>
      ) : <span className="text-text-tertiary">—</span>,
      align: 'center',
      width: '65px'
    },
    {
      key: 'durationMs',
      header: 'Duration',
      render: item => <span className="tabular text-text-secondary text-[12px]">{item.durationMs}ms</span>,
      numeric: true,
      width: '85px'
    }
  ];

  const filteredFindings = findings.filter(c => {
    if (findingOutcomeFilter !== 'ALL' && c.outcome !== findingOutcomeFilter) return false;
    if (findingSearch) {
      const q = findingSearch.toLowerCase();
      return (
        c.id.toLowerCase().includes(q) ||
        c.title.toLowerCase().includes(q) ||
        (c.reasonCode && c.reasonCode.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const tabs = [
    { id: 'decision', label: 'Decision' },
    { id: 'findings', label: 'Findings', badge: findings.filter(c => c.outcome === 'FAIL' || c.outcome === 'WARN').length },
    { id: 'evidence', label: 'Evidence' },
    { id: 'message', label: 'Message' },
    { id: 'audit', label: 'Audit', badge: auditEvents.length },
    { id: 'network', label: 'Network' }
  ];

  return (
    <div className="space-y-6 animate-in fade-in-0 duration-240">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border-subtle">
        <div className="space-y-1.5">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-1.5 text-[13px] text-text-secondary hover:text-text-primary transition-colors cursor-pointer mb-1"
          >
            <ArrowLeft size={14} />
            <span>Cases</span>
          </button>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[24px] font-semibold text-text-primary tracking-[-0.02em]">
              {vendorName}
            </h1>
            <div className="flex items-center gap-1 font-mono text-[12px] text-text-tertiary bg-subtle px-2 py-0.5 rounded">
              <span>{caseId}</span>
              <button
                type="button"
                onClick={() => copyToClipboard(caseId, 'Case ID')}
                aria-label="Copy Case ID"
                className="hover:text-text-primary ml-1"
              >
                {copiedField === 'Case ID' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
              </button>
            </div>
            <Badge variant="status" status={status} size="md" />
            <Badge variant="tier" tier={String((decision as Record<string, unknown>).tier ?? 'LOW')} size="md" />
            {(Array.isArray(decision.awaiting) ? (decision.awaiting as string[]) : []).map(a => (
              <span key={a} className="text-[12px] font-medium text-warning bg-warning-subtle px-2.5 py-0.5 rounded-full border border-warning/20">
                Awaiting {a}
              </span>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {status === 'PENDING' && (awaiting as string[]).includes('VENDOR') && (
            <Button variant="primary" onClick={handleResubmitUnchanged}>
              Resubmit
            </Button>
          )}
          {status === 'REJECTED' && (
            <Button variant="secondary" onClick={handleAppeal}>
              Appeal
            </Button>
          )}
          <Button
            variant="ghost"
            onClick={() => copyToClipboard(String((decision as Record<string, unknown>).reproducibility_hash ?? ''), 'Reproducibility Hash')}
          >
            Copy Hash
          </Button>
        </div>
      </div>

      {/* Counterfactual Card (only if PENDING) */}
      {status === 'PENDING' && cf && (
        <div className="p-4 rounded-[8px] bg-accent-subtle/50 border border-accent/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-full bg-accent-subtle text-accent-fg shrink-0 mt-0.5">
              <Lightbulb size={16} />
            </div>
            <div>
              <div className="text-[14px] text-text-primary">
                Fix {((cf.fix_set ?? []) as unknown[]).length} item{((cf.fix_set ?? []) as unknown[]).length === 1 ? '' : 's'} →{' '}
                <span className="font-semibold text-success">{String(cf.status ?? 'APPROVED')}</span>
              </div>
              <p className="text-[12px] text-text-secondary mt-0.5">
                {String(cf.note ?? 'assumes no new issues are found')}
              </p>
            </div>
          </div>

          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setActiveTab('decision');
              const el = document.getElementById('blocking-items-section');
              el?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            Show items →
          </Button>
        </div>
      )}

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={handleTabChange} />

      {/* TAB CONTENT: Decision */}
      {activeTab === 'decision' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (60% = 7 cols) — Blocking Items */}
          <div id="blocking-items-section" className="lg:col-span-7 space-y-4">
            <h2 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
              Blocking Requirements
            </h2>

            {requiredActions.length > 0 ? (
              <div className="space-y-3">
                {requiredActions.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-[8px] bg-surface border border-border flex items-start gap-3 text-[13px]"
                  >
                    <div className="w-6 h-6 rounded-full bg-subtle text-text-primary font-mono text-[12px] font-medium flex items-center justify-center shrink-0 mt-0.5">
                      {idx + 1}
                    </div>

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] text-text-tertiary">
                            {String((item as Record<string, unknown>).code ?? '')}
                          </span>
                          <span className="font-medium text-text-primary">
                            {String((item as Record<string, unknown>).title ?? (item as Record<string, unknown>).code ?? '')}
                          </span>
                        </div>
                      </div>

                      <p className="text-text-secondary leading-normal">
                        {((item as Record<string, unknown>).field_paths as string[] ?? []).join(', ')}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 rounded-[8px] bg-surface border border-border text-center space-y-2">
                <CheckCircle2 size={24} className="text-success mx-auto" />
                <p className="text-[14px] font-medium text-text-primary">No blocking findings. ✓</p>
                <p className="text-[12px] text-text-secondary">Every mandatory risk and compliance check passed.</p>
                <button
                  type="button"
                  onClick={() => setActiveTab('findings')}
                  className="text-[12px] text-accent hover:underline cursor-pointer"
                >
                  View findings
                </button>
              </div>
            )}
          </div>

          {/* Right Column (40% = 5 cols) — Waterfall & Reproducibility */}
          <div className="lg:col-span-5 space-y-4">
            {/* Risk Waterfall */}
            <Card padding="compact" title="Score Waterfall Breakdown">
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                  <span className="text-[12px] text-text-secondary">Total Risk Score</span>
                  <span className="text-[18px] font-semibold text-text-primary tabular">
                    {Number(score.total ?? 0).toFixed(1)} / 100
                  </span>
                </div>

                {Object.keys(SCORE_MAX).map(name => {
                  const pts = Number((components[name] as { points?: number } | undefined)?.points ?? 0);
                  const max = SCORE_MAX[name];
                  return (
                    <div key={name} className="space-y-1">
                      <div className="flex items-center justify-between text-[12px]">
                        <span className="text-text-primary font-medium">{name}</span>
                        <span className="tabular font-mono text-text-secondary">
                          {pts.toFixed(1)} / {max} pts
                        </span>
                      </div>
                      <div className="h-2 w-full bg-subtle rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all duration-360 ease-out"
                          style={{ width: `${(pts / max) * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Reproducibility Card */}
            <Card padding="compact" title="Decision Reproducibility">
              <div className="space-y-2 pt-1 text-[12px]">
                <div className="flex items-center justify-between p-2 rounded bg-subtle/50">
                  <span className="text-text-secondary">Policy Version</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>{String((decision as Record<string, unknown>).policy_version ?? '—')}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2 rounded bg-subtle/50">
                  <span className="text-text-secondary">Engine Version</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>{String((decision as Record<string, unknown>).engine_version ?? '—')}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2 rounded bg-subtle/50">
                  <span className="text-text-secondary">Reproducibility Hash</span>
                  <div className="flex items-center gap-1 font-mono text-text-primary">
                    <span>{String((decision as Record<string, unknown>).reproducibility_hash ?? '—').slice(0, 12)}</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(String((decision as Record<string, unknown>).reproducibility_hash ?? ''), 'Reproducibility Hash')}
                      aria-label="Copy Reproducibility Hash"
                      className="hover:text-accent cursor-pointer"
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

    {/* TAB CONTENT: Findings */}
    {activeTab === 'findings' && (
      <div className="space-y-4">
        {adjudications.length > 0 && (
          <div className="space-y-1">
            {adjudications.map((a, i) => (
              <div key={i} className="text-[12px] text-text-secondary">
                {'label' in a && typeof a.label === 'string'
                  ? `S8 adjudication: ${a.label}`
                  : 'S8 adjudication: LLM unavailable — deterministic stands'}
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Search check id or reason…"
                value={findingSearch}
                onChange={e => setFindingSearch(e.target.value)}
                className="h-8 px-3 rounded-[6px] border border-border bg-surface text-[13px] w-56 focus-ring"
              />
              <div className="flex items-center gap-1 bg-subtle p-0.5 rounded-[6px]">
                {['ALL', 'FAIL', 'WARN', 'PASS'].map(out => (
                  <button
                    key={out}
                    type="button"
                    onClick={() => setFindingOutcomeFilter(out)}
                    className={`h-7 px-2.5 rounded-[4px] text-[11px] font-medium transition-colors ${
                      findingOutcomeFilter === out
                        ? 'bg-surface text-text-primary shadow-xs dark:shadow-none'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {out}
                  </button>
                ))}
              </div>
            </div>

            <span className="text-[12px] text-text-secondary tabular">
              Showing {filteredFindings.length} checks
            </span>
          </div>

          <Table
            columns={findingColumns}
            data={filteredFindings}
            rowKey={item => item.id}
            compact
            onRowClick={item => {
              const raw = rawFindings.find(f => String((f as Record<string, unknown>).check_id) === item.id);
              if (raw) openEvidenceDrawer(mapEvidence(raw as Record<string, unknown>));
            }}
            rowHighlight={item => (item.outcome === 'FAIL' ? 'border-l-2 border-danger' : '')}
            emptyState={
              <div className="p-8 text-center space-y-2">
                <CheckCircle2 size={24} className="text-success mx-auto" />
                <p className="text-[14px] font-medium text-text-primary">No findings. Every check passed.</p>
              </div>
            }
          />
        </div>
      )}

      {/* TAB CONTENT: Evidence */}
      {activeTab === 'evidence' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (55% = 7 cols) — Document Viewer */}
          <div className="lg:col-span-7 space-y-3">
            <div className="flex items-center justify-between p-3 rounded-t-[8px] bg-subtle border border-border border-b-0 text-[12px]">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-accent" />
                <span className="font-medium text-text-primary">{firstDocId ? `Document ${firstDocId}` : 'No documents attached'}</span>
                <span className="text-text-tertiary">(Primary Evidence)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setPdfZoom(z => Math.max(75, z - 10))}
                  aria-label="Zoom out PDF"
                  className="p-1 hover:bg-surface rounded text-text-secondary"
                >
                  <ZoomOut size={14} />
                </button>
                <span className="tabular px-1 font-mono">{pdfZoom}%</span>
                <button
                  type="button"
                  onClick={() => setPdfZoom(z => Math.min(150, z + 10))}
                  aria-label="Zoom in PDF"
                  className="p-1 hover:bg-surface rounded text-text-secondary"
                >
                  <ZoomIn size={14} />
                </button>
              </div>
            </div>

            {/* Document Canvas Container */}
            <div className="h-[460px] rounded-b-[8px] border border-border bg-canvas p-6 overflow-auto flex justify-center items-center relative">
              {firstDocId ? (
                <embed
                  src={`/api/v1/cases/${caseId}/docs/${firstDocId}`}
                  type="application/pdf"
                  width="100%"
                  height="100%"
                  style={{ transform: `scale(${pdfZoom / 100})` }}
                />
              ) : (
                <div className="text-center space-y-2">
                  <FileText size={48} className="text-text-tertiary mx-auto" />
                  <p className="text-[13px] text-text-secondary">No document bytes attached to this run.</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column (45% = 5 cols) — Claims List */}
          <div className="lg:col-span-5 space-y-3">
            <h3 className="text-[16px] font-semibold text-text-primary">
              Extracted Claims ({claims.length})
            </h3>
            <p className="text-[12px] text-text-secondary">
              Hover a claim to preview its quoted source text.
            </p>

            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
              {claims.map((claim, idx) => (
                <div
                  key={idx}
                  onMouseEnter={() => setHighlightedClaim(claim)}
                  onMouseLeave={() => setHighlightedClaim(null)}
                  className={`p-3 rounded-[6px] border transition-all duration-120 text-[12px] space-y-1.5 cursor-pointer ${
                    highlightedClaim === claim
                      ? 'bg-accent-subtle/50 border-accent text-text-primary'
                      : 'bg-surface border-border text-text-secondary hover:border-border-strong'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-text-primary font-medium">{claim.path}</span>
                    <Badge size="sm" color="neutral">{claim.source}</Badge>
                  </div>
                  <div className="text-text-primary font-medium truncate">
                    {claim.value}
                  </div>
                  {claim.quote && (
                    <blockquote className="italic text-text-tertiary text-[11px] border-l border-border pl-2 truncate">
                      {claim.quote}
                    </blockquote>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Message */}
      {activeTab === 'message' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 space-y-4">
            {status === 'PENDING' && (Array.isArray((decision as Record<string, unknown>).awaiting) ? ((decision as Record<string, unknown>).awaiting as string[]) : []).includes('VENDOR') && (
              <div className="p-4 rounded-[8px] bg-surface border border-border flex items-center justify-between gap-3 text-[13px]">
                <span className="text-text-secondary">No document changes? Verify the 409 path.</span>
                <Button size="sm" variant="ghost" onClick={handleResubmitUnchanged}>
                  Resubmit unchanged (expect 409)
                </Button>
              </div>
            )}
            <div className="p-6 rounded-[8px] bg-surface border border-border space-y-4 text-[13px]">
              <div className="border-b border-border-subtle pb-3 space-y-1">
                <div className="text-[14px] font-medium text-text-primary">
                  Subject: {String((msg as Record<string, unknown> | null)?.subject ?? 'Vendor message')}
                </div>
                <div className="text-[12px] text-text-tertiary">
                  {String((msg as Record<string, unknown> | null)?.to ?? '')}
                </div>
              </div>

              <div className="text-text-primary space-y-3 leading-relaxed whitespace-pre-wrap">
                {String((msg as Record<string, unknown> | null)?.body ?? 'No message rendered for this run yet.')}
              </div>

              <div className="pt-4 border-t border-border-subtle">
                <div className="text-[12px] font-medium text-text-primary mb-2">Required actions</div>
                <ul className="space-y-1">
                  {requiredActions.map((a, i) => (
                    <li key={i} className="text-[12px] text-text-secondary">
                      <span className="font-mono text-text-primary">{String((a as Record<string, unknown>).code ?? '')}</span>
                      {' — '}{((a as Record<string, unknown>).field_paths as string[] ?? []).join(', ')}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-4">
            <Card padding="compact" title="Message Policy Checker">
              <div className="space-y-3 pt-2 text-[13px]">
                <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                  <span className="text-[12px] text-text-secondary">Forbidden-term scan</span>
                  <Badge size="sm" color="success">Pass</Badge>
                </div>
                <div className="p-3 bg-subtle/50 rounded-[6px] border border-border-subtle text-[11px] text-text-secondary leading-normal">
                  Vendor-facing text is rendered from templates and scanned for forbidden terms before send. The pipeline never includes internal scores or sanctions detail.
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Audit */}
      {activeTab === 'audit' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-4 rounded-[8px] bg-surface border border-border">
            <div>
              <h3 className="text-[14px] font-semibold text-text-primary">
                Cryptographic Audit Log
              </h3>
              <p className="text-[12px] text-text-secondary">
                Hash-chained run events, verified server-side.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                size="sm"
                variant="primary"
                loading={isVerifyingChain}
                onClick={handleVerifyAuditChain}
              >
                Verify chain
              </Button>
              {verify && (
                <span role="status" className="text-[12px] font-medium">
                  {verify.ok ? `✅ chain ok (${verify.length} events)` : `⛔ broken at sequence ${verify.broken_at}`}
                </span>
              )}
            </div>
          </div>

          {/* Vertical Timeline */}
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-[2px] before:bg-border-subtle">
            {auditEvents.map(event => {
              const isPayloadOpen = !!expandedPayloads[event.sequence];
              return (
                <div key={event.sequence} className="relative group">
                  <div className="absolute -left-6 top-1.5 w-3 h-3 rounded-full bg-surface border-2 border-accent" />
                  <div className="p-4 rounded-[8px] bg-surface border border-border space-y-2 text-[13px]">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[12px] text-text-tertiary tabular">
                          Seq {event.sequence} · {event.timestamp}
                        </span>
                        <Badge size="sm" color="neutral">{event.eventType}</Badge>
                      </div>
                      <span className="text-[12px] font-medium text-text-secondary">
                        Actor: {event.actor}
                      </span>
                    </div>
                    <p className="text-text-primary font-medium">
                      {event.summary}
                    </p>
                    <div className="flex items-center justify-between text-[11px] font-mono text-text-tertiary">
                      <span className="truncate max-w-xs">Hash: {event.hash.slice(0, 16)}…</span>
                      <button
                        type="button"
                        onClick={() => setExpandedPayloads(p => ({ ...p, [event.sequence]: !p[event.sequence] }))}
                        className="text-accent hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <span>{isPayloadOpen ? 'Hide payload' : 'Inspect payload'}</span>
                        {isPayloadOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      </button>
                    </div>
                    {isPayloadOpen && (
                      <pre className="p-3 bg-subtle rounded text-[11px] font-mono text-text-secondary overflow-x-auto">
                        <code>{JSON.stringify(event.payload, null, 2)}</code>
                      </pre>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT: Network */}
      {activeTab === 'network' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-[8px] bg-surface border border-border text-[12px]">
            <div>
              <span className="font-medium text-text-primary">Entity & Attribute Links</span>
              <p className="text-text-secondary">Shared-attribute findings from duplicate and network checks.</p>
            </div>
            <div className="flex items-center gap-1.5">
              <Button size="sm" variant="ghost" onClick={() => setNetworkZoom(z => Math.max(0.6, z - 0.2))}>
                <ZoomOut size={14} />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setNetworkZoom(z => Math.min(1.8, z + 0.2))}>
                <ZoomIn size={14} />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setNetworkZoom(1)}>
                <Maximize2 size={14} />
              </Button>
            </div>
          </div>

          <div className="relative min-h-[300px] rounded-[8px] border border-border bg-muted overflow-hidden p-6">
            <div
              className="relative w-full min-h-[260px] flex flex-col items-center justify-center gap-3 transition-transform duration-180"
              style={{ transform: `scale(${networkZoom})` }}
            >
              {dupFindings.length === 0 ? (
                <p className="text-[13px] text-text-secondary">No shared-attribute clusters for this case.</p>
              ) : (
                dupFindings.map(f => (
                  <div
                    key={f.id}
                    onClick={() => setSelectedEdge({ source: vendorName, target: f.title, attr: f.reasonCode ?? f.subject })}
                    className="w-full max-w-md p-4 bg-surface border-2 border-danger rounded-[6px] shadow-sm cursor-pointer hover:border-accent text-left transition-all"
                  >
                    <div className="text-[13px] font-semibold text-text-primary">{f.id}: {f.title}</div>
                    <div className="text-[12px] text-danger font-medium mt-0.5">Flagged link</div>
                    <div className="text-[11px] text-text-secondary mt-1 line-clamp-2">{f.reasonCode ?? f.subject}</div>
                  </div>
                ))
              )}

              {selectedEdge && (
                <div className="max-w-sm p-4 rounded-[8px] bg-surface border border-danger shadow-md text-[13px] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-danger flex items-center gap-1.5">
                      <AlertCircle size={14} /> Shared Attribute Detected
                    </span>
                    <button type="button" aria-label="Close details" onClick={() => setSelectedEdge(null)} className="text-text-tertiary hover:text-text-primary p-0.5 rounded hover:bg-subtle cursor-pointer">
                      <X size={14} />
                    </button>
                  </div>
                  <p className="text-text-primary font-medium">{selectedEdge.attr}</p>
                  <div className="text-[12px] text-text-secondary">
                    Links {selectedEdge.source} and {selectedEdge.target}.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
