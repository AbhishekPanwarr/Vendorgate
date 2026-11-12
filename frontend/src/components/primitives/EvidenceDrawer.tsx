import React, { useState } from 'react';
import { Drawer } from './Drawer';
import { Badge } from './Badge';
import { Button } from './Button';
import { Checkbox } from './Checkbox';
import { ExternalLink, FileCode, Cpu, ShieldCheck, Check, Sparkles } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const EvidenceDrawer: React.FC = () => {
  const { activeEvidence, closeEvidenceDrawer, navigate, addToast } = useApp();
  const [markedReviewed, setMarkedReviewed] = useState(false);

  if (!activeEvidence) return null;

  return (
    <Drawer
      isOpen={!!activeEvidence}
      onClose={closeEvidenceDrawer}
      width="wide" // 640px wide per §10
      title={
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
              {activeEvidence.title}
            </span>
            <span className="font-mono text-[12px] text-text-tertiary">
              {activeEvidence.checkId}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="status" status={activeEvidence.outcome} size="sm" />
            <Badge variant="generic" color={activeEvidence.severity === 'HIGH' ? 'danger' : 'warning'} size="sm">
              {activeEvidence.severity}
            </Badge>
          </div>
        </div>
      }
      subtitle={activeEvidence.subtitle}
      headerActions={
        <Button
          size="sm"
          variant="ghost"
          rightIcon={<ExternalLink size={14} />}
          onClick={() => {
            navigate('/policy');
            closeEvidenceDrawer();
          }}
        >
          Check docs
        </Button>
      }
      footer={
        <>
          <Checkbox
            label="Mark as reviewed (session)"
            checked={markedReviewed}
            onChange={e => setMarkedReviewed(e.target.checked)}
          />
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(activeEvidence, null, 2));
                addToast({ title: 'Evidence bundle copied to clipboard', variant: 'default' });
              }}
            >
              Copy bundle
            </Button>
            <Button size="sm" variant="secondary" onClick={closeEvidenceDrawer}>
              Close
            </Button>
          </div>
        </>
      }
    >
      {/* Section 1: Details */}
      <div className="space-y-3">
        <h4 className="text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary">
          Details
        </h4>
        <div className="grid grid-cols-2 gap-3 p-4 rounded-[8px] bg-subtle/50 border border-border-subtle text-[13px]">
          <div>
            <span className="text-[12px] text-text-secondary block">Reason code</span>
            <span className="font-mono text-[12px] font-medium text-text-primary">{activeEvidence.reasonCode}</span>
          </div>
          <div>
            <span className="text-[12px] text-text-secondary block">Fixed by</span>
            <span className="font-medium text-text-primary">{activeEvidence.fixedBy}</span>
          </div>
          <div>
            <span className="text-[12px] text-text-secondary block">Execution duration</span>
            <span className="tabular font-medium text-text-primary">{activeEvidence.durationMs}ms</span>
          </div>
          <div>
            <span className="text-[12px] text-text-secondary block">Deterministic rule</span>
            <Badge size="sm" color={activeEvidence.deterministic ? 'success' : 'info'}>
              {activeEvidence.deterministic ? 'Yes (Static rule)' : 'No (Probabilistic)'}
            </Badge>
          </div>
        </div>
      </div>

      {/* Section 2: Evidence (grouped by kind) */}
      <div className="space-y-3">
        <h4 className="text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary">
          Evidence Items ({activeEvidence.items.length})
        </h4>
        <div className="space-y-3">
          {activeEvidence.items.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-[8px] bg-surface border border-border space-y-2 text-[13px]"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge size="sm" color={item.kind === 'claim' ? 'accent' : item.kind === 'adapter' ? 'info' : 'neutral'}>
                    {item.kind.toUpperCase()}
                  </Badge>
                  <span className="font-mono text-[12px] text-text-tertiary">{item.ref}</span>
                </div>
              </div>

              <p className="text-text-primary font-medium">{item.summary}</p>

              {item.claimDetails && (
                <div className="p-3 bg-subtle/40 rounded-[6px] border border-border-subtle space-y-1.5 text-[12px]">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-text-secondary">{item.claimDetails.path}</span>
                    <Badge size="sm" color="neutral">{item.claimDetails.source}</Badge>
                  </div>
                  <div className="font-medium text-text-primary">
                    Raw value: <span className="font-mono text-accent-fg bg-accent-subtle/50 px-1 py-0.5 rounded">{item.claimDetails.rawValue}</span>
                  </div>
                  {item.claimDetails.quote && (
                    <blockquote className="italic text-text-secondary border-l-2 border-accent/40 pl-2.5 py-0.5">
                      {item.claimDetails.quote}
                    </blockquote>
                  )}
                </div>
              )}

              {item.adapterDetails && (
                <div className="grid grid-cols-2 gap-2 p-3 bg-subtle/40 rounded-[6px] border border-border-subtle text-[12px]">
                  <div>Call ID: <span className="font-mono text-text-primary">{item.adapterDetails.callId}</span></div>
                  <div>Version: <span className="font-mono text-text-primary">{item.adapterDetails.version}</span></div>
                  <div>Latency: <span className="tabular font-medium text-text-primary">{item.adapterDetails.latencyMs}ms</span></div>
                  <div>Timestamp: <span className="tabular text-text-tertiary">{item.adapterDetails.retrievedAt}</span></div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Rule / policy reference */}
      <div className="space-y-3">
        <h4 className="text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary">
          Rule & Policy Reference
        </h4>
        <div className="space-y-2">
          <div className="rounded-[8px] bg-subtle border border-border overflow-hidden">
            <div className="px-3 py-1.5 border-b border-border-subtle bg-canvas text-[11px] font-mono text-text-tertiary flex items-center gap-1.5">
              <FileCode size={13} />
              <span>policy/checks/name_matching.ts</span>
            </div>
            <pre className="p-3 text-[12px] font-mono text-text-primary overflow-x-auto leading-relaxed">
              <code>{activeEvidence.ruleSnippet}</code>
            </pre>
          </div>

          <div className="rounded-[8px] bg-subtle border border-border overflow-hidden">
            <div className="px-3 py-1.5 border-b border-border-subtle bg-canvas text-[11px] font-mono text-text-tertiary flex items-center gap-1.5">
              <ShieldCheck size={13} />
              <span>policy/base.yaml (slice)</span>
            </div>
            <pre className="p-3 text-[12px] font-mono text-text-secondary overflow-x-auto leading-relaxed">
              <code>{activeEvidence.policySlice}</code>
            </pre>
          </div>
        </div>
      </div>

      {/* Section 4: LLM Rationale (if any) */}
      {activeEvidence.llmRationale && (
        <div className="space-y-3 p-4 rounded-[8px] bg-accent-subtle/30 border border-accent/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-accent-fg font-medium text-[13px]">
              <Cpu size={16} />
              <span>LLM Adjudication Rationale</span>
            </div>
            <Badge size="sm" color="accent">
              Confidence: {Math.round(activeEvidence.llmRationale.confidence * 100)}%
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[12px]">
            <div>Verdict: <span className="font-semibold text-text-primary">{activeEvidence.llmRationale.verdict}</span></div>
            <div>Order-swap consistent: <span className="font-medium text-success">{activeEvidence.llmRationale.orderSwapConsistent ? 'Verified ✓' : 'No'}</span></div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] text-text-tertiary uppercase font-medium">Corroborators (Ground Truth):</span>
            <div className="flex flex-wrap gap-1.5">
              {activeEvidence.llmRationale.corroborators.map(cor => (
                <span key={cor} className="text-[11px] font-mono bg-surface border border-accent/30 text-accent-fg px-2 py-0.5 rounded">
                  {cor}
                </span>
              ))}
            </div>
          </div>

          <div className="p-2.5 rounded bg-surface/80 border border-border-subtle text-[12px] text-text-secondary leading-normal italic">
            "{activeEvidence.llmRationale.note}"
          </div>
        </div>
      )}
    </Drawer>
  );
};
