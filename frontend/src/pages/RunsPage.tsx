import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { Card } from '../components/primitives/Card';
import { useApp } from '../context/AppContext';
import { api, mapCheck, mapEvidence, mapRun } from '../api';
import type { Stage, CheckItem } from '../types';
import {
  Check,
  Zap,
  ExternalLink,
  Copy,
  ChevronRight,
  FileCheck,
  AlertCircle
} from 'lucide-react';

const STAGE_NAMES: Record<string, string> = {
  S0: 'Intake', S1: 'Documents', S2: 'Completeness', S3: 'Format', S4: 'Verification',
  S5: 'Consistency', S6: 'Duplicates', S7: 'Screening', S8: 'Adjudication',
  S9: 'Scoring', S10: 'Decision', S11: 'Comms', S12: 'Persist',
};

export const RunsPage: React.FC<{ runIdProp?: string }> = ({ runIdProp }) => {
  const { currentPath, navigate, runs, openEvidenceDrawer, addToast } = useApp();

  const pathParts = currentPath.split('/');
  const runId = runIdProp || pathParts[2] || runs[0]?.id;

  const [pack, setPack] = useState<Record<string, unknown> | null>(null);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!runId) return;
    let live = true;
    setPack(null);
    api.getRun(runId).then(p => { if (live) setPack(p as Record<string, unknown>); })
      .catch(() => { if (live) setLoadError('Run not found.'); });
    return () => { live = false; };
  }, [runId]);

  const run = React.useMemo(() => {
    if (!pack) return undefined;
    return mapRun(pack as never);
  }, [pack]);

  const findings = React.useMemo(
    () => (Array.isArray(pack?.findings) ? (pack?.findings as Record<string, unknown>[]) : []),
    [pack],
  );

  const checksStream: CheckItem[] = React.useMemo(
    () => findings.map(f => mapCheck(f, String((f as Record<string, unknown>).stage ?? 'S?'))),
    [findings],
  );

  const stagesList: Stage[] = React.useMemo(() => {
    const codes = ['S0','S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S11','S12'];
    const counts: Record<string, number> = {};
    for (const f of findings) {
      const s = String((f as Record<string, unknown>).stage ?? '?');
      counts[s] = (counts[s] ?? 0) + 1;
    }
    return codes.map((code, i) => ({
      id: `s${i}`, code, name: STAGE_NAMES[code] ?? code,
      checksCount: counts[code] ?? 0, status: 'completed' as const,
    }));
  }, [findings]);

  const delta = (pack?.delta ?? null) as null | { rerun?: number; cached?: number; resolved?: string[]; introduced?: string[] };
  const [showDelta, setShowDelta] = useState(false);
  const [activeStageId, setActiveStageId] = useState<string>('s4');

  // SVG 240° Arc Gauge Calculation
  // 240 degrees arc: from 150 deg to 390 deg
  const score = run ? run.score : 38.5;
  const radius = 70;
  const strokeWidth = 8;
  const arcTotalDeg = 240;
  // Circumference of 240 degree sector
  const totalLength = (arcTotalDeg / 360) * (2 * Math.PI * radius);
  const fillOffset = totalLength - (score / 100) * totalLength;

  if (!run) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-center space-y-4">
        {/* Custom SVG line-art document illustration without emojis */}
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none" className="text-text-tertiary">
          <rect x="24" y="16" width="72" height="88" rx="8" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
          <path d="M40 36H80" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <path d="M40 50H70" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <path d="M40 64H60" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <circle cx="76" cy="76" r="14" fill="var(--bg-surface)" stroke="var(--accent)" strokeWidth="2" />
          <path d="M71 76L74 79L82 71" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>

        <h2 className="text-[20px] font-semibold text-text-primary">No run selected</h2>
        <p className="text-[13px] text-text-secondary max-w-sm">
          Pick a case from the dashboard or submit a new vendor to observe live 13-stage verification execution.
        </p>
        <Button variant="primary" onClick={() => navigate('/submit')}>
          Submit vendor →
        </Button>
      </div>
    );
  }

  const completedChecksCount = checksStream.length;
  const runningChecksCount = 0;
  const blockingCount = checksStream.filter(c => c.outcome === 'FAIL').length;

  return (
    <div className="space-y-6 animate-in fade-in-0 duration-240">
      {/* Run Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border-subtle">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[13px] font-semibold text-text-primary bg-subtle px-2 py-0.5 rounded">
              {run.id}
            </span>
            <span className="text-[13px] text-text-secondary">
              for <span className="font-medium text-text-primary">{run.vendorName}</span>
            </span>
            <Badge variant="status" status={run.status} size="sm" />
          </div>
          {showDelta && delta ? (
            <p className="text-[12px] text-text-tertiary">
              Delta run · {delta.rerun ?? 0} re-ran · {delta.cached ?? 0} cached
            </p>
          ) : (
            <p className="text-[12px] text-text-tertiary">
              Full verification pipeline · {run.submittedAt} · {run.durationMs}ms duration
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setShowDelta(v => !v);
              addToast({
                title: showDelta ? 'Switched to Full Run view' : 'Switched to Delta Run mode',
                description: showDelta ? 'Displaying all 13 stages fresh' : 'Displaying cached vs re-run diffs',
                variant: 'default'
              });
            }}
            disabled={!delta}
            title={delta ? 'Toggle delta diff view' : 'No delta for this run'}
          >
            {showDelta ? 'Full mode' : 'Toggle delta'}
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              navigator.clipboard.writeText(run.id);
              addToast({ title: 'Run ID copied to clipboard', variant: 'default' });
            }}
          >
            Copy ID
          </Button>

          <Button
            size="sm"
            variant="secondary"
            onClick={() => navigate(`/cases/${run.caseId}`)}
          >
            View case →
          </Button>
        </div>
      </div>

      {/* Desktop 3-Column Grid: 20% / 55% / 25% */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Col 1 — Stage Rail (sticky, 20% = ~2.5 cols -> 3 cols) */}
        <div className="lg:col-span-3 space-y-2 sticky top-20 max-h-[75vh] overflow-y-auto pr-1">
          <div className="text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary px-1 pb-1">
            Pipeline Stages (13)
          </div>

          <div className="relative pl-1">
            {stagesList.map((st, idx) => {
              const isActive = st.id === activeStageId;
              const isCompleted = st.status === 'completed';

              return (
                <div key={st.id} className="relative flex items-center gap-3 h-11 group">
                  {/* Vertical connecting line */}
                  {idx < stagesList.length - 1 && (
                    <div
                      className={`absolute left-[11px] top-6 bottom-0 w-[2px] transition-colors duration-240 ${
                        isCompleted ? 'bg-accent' : 'bg-border'
                      }`}
                    />
                  )}

                  {/* Stage state indicator (24px circle) */}
                  <div
                    onClick={() => setActiveStageId(st.id)}
                    className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center text-[12px] transition-all duration-180 cursor-pointer select-none ${
                      isCompleted
                        ? 'bg-accent text-white scale-100'
                        : st.status === 'running'
                        ? 'border-2 border-accent text-accent animate-spin'
                        : 'border border-border text-text-tertiary bg-surface'
                    }`}
                  >
                    {isCompleted ? (
                      <Check size={13} strokeWidth={3} />
                    ) : (
                      <span className="text-[10px] font-mono">{st.code}</span>
                    )}
                  </div>

                  {/* Label and Check counts */}
                  <div
                    onClick={() => setActiveStageId(st.id)}
                    className={`flex-1 flex items-center justify-between text-[13px] px-2 py-1 rounded-[6px] transition-colors cursor-pointer ${
                      isActive
                        ? 'bg-surface font-medium text-text-primary border-l-2 border-accent shadow-xs'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      <span>{st.code}</span>
                      <span className="truncate">{st.name}</span>
                    </div>

                    <div className="flex items-center gap-1 text-[11px] text-text-tertiary font-mono">
                      {(showDelta && delta) ? <Zap size={11} className="text-accent" /> : null}
                      <span>{st.checksCount}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Col 2 — Check Stream (55% = ~6.5 cols -> 6 cols) */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              <span className="text-[13px] font-medium text-text-primary">
                Checks · {completedChecksCount} completed · {runningChecksCount} running
              </span>
            </div>
            <span className="text-[11px] text-text-tertiary font-mono">
              Snapshot
            </span>
          </div>

          {/* Cards Stream */}
          <div aria-live="polite" className="space-y-2">
            {checksStream.map((chk, idx) => {
              const isFail = chk.outcome === 'FAIL';
              const isWarn = chk.outcome === 'WARN';

              return (
                <div
                  key={chk.id}
                  className={`p-3 rounded-[6px] border bg-surface transition-all duration-180 space-y-1.5 ${
                    isFail
                      ? 'border-danger/50 shadow-xs'
                      : chk.cached
                      ? 'bg-subtle/40 border-border-subtle'
                      : 'border-border'
                  }`}
                >
                  {/* Row 1: Check ID, Outcome Badge, Duration, Cached */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[12px] text-text-tertiary font-medium">
                        {chk.id}
                      </span>
                      {chk.cached && (
                        <span className="inline-flex items-center gap-0.5 text-[11px] text-accent font-medium bg-accent-subtle/50 px-1.5 py-0.2 rounded">
                          <Zap size={11} className="fill-accent" />
                          <span>Cached</span>
                        </span>
                      )}
                      {showDelta && delta && (delta.resolved ?? []).includes(chk.id) && (
                        <span className="text-[11px] font-medium text-success bg-success-subtle px-1.5 py-0.2 rounded line-through">
                          Resolved in v2
                        </span>
                      )}
                      {showDelta && delta && (delta.introduced ?? []).includes(chk.id) && (
                        <span className="text-[11px] font-medium text-warning bg-warning-subtle px-1.5 py-0.2 rounded">
                          Introduced after fix
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="tabular text-[12px] text-text-tertiary font-mono">
                        {chk.durationMs}ms
                      </span>
                      <Badge variant="status" status={chk.outcome} size="sm" />
                    </div>
                  </div>

                  {/* Row 2: Title & Subject */}
                  <div className="flex items-baseline justify-between gap-2">
                    <div className="truncate">
                      <div className="text-[13px] font-medium text-text-primary truncate">
                        {chk.title}
                      </div>
                      <div className="text-[12px] text-text-secondary truncate">
                        {chk.subject}
                      </div>
                    </div>

                    {(isFail || isWarn || chk.evidenceRef) && (
                      <button
                        type="button"
                        onClick={() => {
                          const raw = findings.find(ff => (ff as Record<string, unknown>).check_id === chk.id);
                          openEvidenceDrawer(mapEvidence(((raw ?? {}) as Record<string, unknown>)));
                        }}
                        className="text-[12px] font-medium text-accent hover:underline flex items-center gap-0.5 shrink-0 cursor-pointer"
                      >
                        <span>evidence</span>
                        <ChevronRight size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Col 3 — Risk Panel (sticky, 25% = 3 cols) */}
        <div className="lg:col-span-3 space-y-4 sticky top-20">
          <Card padding="compact" title="Decision Risk Panel">
            <div className="space-y-4 pt-1">
              <div>
                <span className="text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary block">
                  Risk Score
                </span>
                <div className="flex items-baseline gap-1 my-1">
                  <span className="text-[30px] font-semibold text-text-primary tabular tracking-tight">
                    {score.toFixed(1)}
                  </span>
                  <span className="text-[14px] text-text-tertiary">/100</span>
                </div>
              </div>

              {/* Arc Gauge (SVG 240 degrees) */}
              <div className="relative w-full flex items-center justify-center py-2">
                <svg width="180" height="120" viewBox="0 0 180 120" className="overflow-visible">
                  {/* Gauge background track */}
                  <path
                    d="M 25 105 A 70 70 0 1 1 155 105"
                    fill="none"
                    stroke="var(--bg-subtle)"
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                  />
                  {/* Gauge filled arc */}
                  <path
                    d="M 25 105 A 70 70 0 1 1 155 105"
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    strokeDasharray={totalLength}
                    strokeDashoffset={fillOffset}
                    className="transition-all duration-600 ease-[cubic-bezier(0.16,1,0.3,1)]"
                  />
                </svg>
                <div className="absolute bottom-1 left-0 right-0 text-center">
                  <Badge variant="tier" tier={run.tier} size="sm" />
                </div>
              </div>

              {/* Waterfall: 6 components */}
              <div className="space-y-2 pt-2 border-t border-border-subtle">
                <div className="text-[11px] uppercase tracking-[0.04em] text-text-tertiary">
                  Component Weights
                </div>
                {run.riskComponents.map(c => (
                  <div key={c.name} className="space-y-1">
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="text-text-secondary truncate">{c.name}</span>
                      <span className="tabular font-mono text-text-primary font-medium">
                        {c.points.toFixed(1)}
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-subtle rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all duration-360 ease-out"
                        style={{ width: `${(c.points / c.max) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Counters */}
              <div className="pt-3 border-t border-border-subtle text-[11px] font-mono text-text-tertiary space-y-1">
                <div>Claims: {run.claimsCount} · Cache: {run.cacheHitCount}/{run.totalChecks}</div>
                <div>LLM: {run.llmCalls} calls · Cost: ${run.costUsd.toFixed(3)}</div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Bottom Sticky Decision Banner */}
      <div
        aria-live="assertive"
        className={`w-full p-5 rounded-[8px] bg-surface border-t-2 shadow-md dark:shadow-none transition-all duration-240 ${
          run.status === 'APPROVED'
            ? 'border-t-success bg-success-subtle/20'
            : run.status === 'REJECTED'
            ? 'border-t-danger'
            : 'border-t-warning'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start sm:items-center gap-3">
            <Badge variant="status" status={run.status} size="lg" />
            <div>
              <div className="text-[16px] font-semibold text-text-primary">
                {run.status === 'PENDING'
                  ? 'PENDING (awaiting VENDOR)'
                  : run.status === 'APPROVED'
                  ? 'APPROVED — Automatic Gate Pass'
                  : 'REJECTED — Sanctions or Entity Discrepancy'}
              </div>
              <p className="text-[13px] text-text-secondary mt-0.5">
                {run.status === 'PENDING'
                  ? `${blockingCount} blocking item${blockingCount === 1 ? '' : 's'} open · resolve vendor items to proceed`
                  : run.status === 'APPROVED'
                  ? 'All checks verified without blocking exceptions.'
                  : 'Critical discrepancy encountered during verification.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {showDelta && delta ? (
              <span className="text-[13px] text-text-tertiary">
                Delta vs previous version
              </span>
            ) : null}
            <Button
              variant="primary"
              size="md"
              onClick={() => navigate(`/cases/${run.caseId}`)}
            >
              Open case →
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
