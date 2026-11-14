import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { Card } from '../components/primitives/Card';
import { Textarea } from '../components/primitives/Textarea';
import { Checkbox } from '../components/primitives/Checkbox';
import { Dialog } from '../components/primitives/Dialog';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import { Tooltip } from '../components/primitives/Tooltip';
import { useApp } from '../context/AppContext';
import type { CaseRecord } from '../types';
import {
  CheckSquare,
  ShieldAlert,
  PhoneCall,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  HelpCircle,
  AlertCircle
} from 'lucide-react';

export const ApprovalsPage: React.FC = () => {
  const { cases, role, approveCase, rejectCase, requestInfoCase, verifyCallbackDesk, addToast } = useApp();

  // Queue selection
  const [selectedQueue, setSelectedQueue] = useState<string>('All');

  // Filter cases matching queue
  const queueFilteredCases = cases.filter(c => {
    if (selectedQueue === 'All') return c.status === 'PENDING';
    if (selectedQueue === 'AP Analyst') return c.awaitingRole === 'AP Analyst';
    if (selectedQueue === 'Controller') return c.awaitingRole === 'Controller';
    if (selectedQueue === 'Compliance') return c.awaitingRole === 'Compliance';
    if (selectedQueue === 'Appeals') return c.status === 'REJECTED';
    return true;
  });

  const [selectedCaseId, setSelectedCaseId] = useState<string>('');

  const activeCase = cases.find(c => c.id === selectedCaseId);

  // Approval Form state
  const [approvalNote, setApprovalNote] = useState('');
  const [reviewedFindings, setReviewedFindings] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  // Callback Desk Modal state
  const [isCallbackOpen, setIsCallbackOpen] = useState(false);
  const [callbackDialedNumber, setCallbackDialedNumber] = useState('');
  const [callbackNumberSource, setCallbackNumberSource] = useState<'master' | 'registry' | 'public' | 'request'>('master');
  const [callbackOutcome, setCallbackOutcome] = useState('reached');
  const [callbackAttested, setCallbackAttested] = useState(false);
  const [callbackResult, setCallbackResult] = useState<{ success: boolean; message: string } | null>(null);

  // Check Segregation of Duties (SoD)
  const currentActorEmail = 'panwarabhishek629@gmail.com';
  const isSoDViolated = activeCase && activeCase.requesterEmail === currentActorEmail;

  // Queue counts
  const countAP = cases.filter(c => c.awaitingRole === 'AP Analyst').length;
  const countController = cases.filter(c => c.awaitingRole === 'Controller').length;
  const countCompliance = cases.filter(c => c.awaitingRole === 'Compliance').length;
  const countAppeals = cases.filter(c => c.status === 'REJECTED').length;
  const countAll = cases.filter(c => c.status === 'PENDING').length;

  const queues = [
    { id: 'All', label: 'All', count: countAll },
    { id: 'AP Analyst', label: 'AP Analyst', count: countAP },
    { id: 'Controller', label: 'Controller', count: countController },
    { id: 'Compliance', label: 'Compliance', count: countCompliance },
    { id: 'Appeals', label: 'Appeals', count: countAppeals },
  ];

  const handleApprove = async () => {
    if (!activeCase) return;
    if (!approvalNote.trim()) {
      addToast({ title: 'Approval note is required', variant: 'warning' });
      return;
    }
    setIsApproving(true);
    try {
      const res = await approveCase(activeCase.id, approvalNote);
      if (res.success) {
        setApprovalNote('');
        setReviewedFindings(false);
      } else {
        addToast({ title: res.error ?? 'Approval rejected', variant: 'danger' });
      }
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    if (!activeCase) return;
    const res = await rejectCase(activeCase.id, approvalNote || 'Rejected after review');
    if (!res.success) addToast({ title: res.error ?? 'Reject failed', variant: 'danger' });
  };

  const handleRequestInfo = async () => {
    if (!activeCase) return;
    const res = await requestInfoCase(activeCase.id, approvalNote || 'Information request dispatched');
    if (!res.success) addToast({ title: res.error ?? 'Request failed', variant: 'danger' });
  };

  const handleCallbackSubmit = async () => {
    if (!activeCase) return;
    const sourceMap: Record<string, string> = {
      master: 'VENDOR_MASTER', registry: 'REGISTRY', public: 'PUBLIC_DIRECTORY', request: 'FROM_REQUEST',
    };
    const res = await verifyCallbackDesk(
      activeCase.id,
      sourceMap[callbackNumberSource] ?? callbackNumberSource,
      callbackDialedNumber || '+49 30 5551234',
    );
    setCallbackResult(res);
  };

  return (
    <div className="space-y-6 animate-in fade-in-0 duration-240">
      <PageHeader
        title="Approvals Queue"
        description="Review triage requests, enforce segregation of duties, and conduct out-of-band callbacks."
      />

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Queue Sidebar (3 cols on desktop) */}
        <div className="md:col-span-3 space-y-1 rounded-[8px] bg-muted border border-border-subtle p-2">
          <div className="px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Queues
          </div>

          {queues.map(q => {
            const isActive = selectedQueue === q.id;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => {
                  setSelectedQueue(q.id);
                  const first = cases.find(c => {
                    if (q.id === 'All') return c.status === 'PENDING';
                    if (q.id === 'AP Analyst') return c.awaitingRole === 'AP Analyst';
                    if (q.id === 'Controller') return c.awaitingRole === 'Controller';
                    if (q.id === 'Compliance') return c.awaitingRole === 'Compliance';
                    if (q.id === 'Appeals') return c.status === 'REJECTED';
                    return true;
                  });
                  if (first) setSelectedCaseId(first.id);
                }}
                className={`w-full h-9 px-3 flex items-center justify-between rounded-[6px] text-[13px] transition-colors cursor-pointer select-none ${
                  isActive
                    ? 'bg-surface text-text-primary font-medium border-l-2 border-accent shadow-xs dark:shadow-none'
                    : 'text-text-secondary hover:text-text-primary hover:bg-subtle'
                }`}
              >
                <span>{q.label}</span>
                <span className={`text-[11px] font-mono tabular px-1.5 py-0.2 rounded-full ${
                  isActive ? 'bg-accent-subtle text-accent-fg' : 'bg-subtle text-text-tertiary'
                }`}>
                  {q.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Main Content Area (9 cols) — Two-column split: List (40%) / Detail (60%) */}
        <div className="md:col-span-9 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* List Column (40% = 5 cols) */}
          <div className="lg:col-span-5 space-y-2">
            <div className="flex items-center justify-between text-[12px] text-text-secondary pb-1 px-1">
              <span>{queueFilteredCases.length} cases waiting</span>
              <span className="font-mono">Queue: {selectedQueue}</span>
            </div>

            {queueFilteredCases.length === 0 ? (
              <div className="p-8 rounded-[8px] bg-surface border border-border text-center space-y-2">
                <CheckCircle2 size={24} className="text-success mx-auto" />
                <p className="text-[14px] font-medium text-text-primary">Nothing waiting for you. Nice.</p>
                <p className="text-[12px] text-text-secondary">All cases in this queue have been resolved.</p>
              </div>
            ) : (
              queueFilteredCases.map(c => {
                const isSelected = c.id === activeCase?.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedCaseId(c.id)}
                    className={`p-3.5 rounded-[8px] border transition-all duration-120 cursor-pointer space-y-2 select-none ${
                      isSelected
                        ? 'bg-accent-subtle/50 border-accent border-l-2 text-text-primary shadow-xs'
                        : 'bg-surface border-border hover:bg-subtle/60 text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {/* Row 1: Vendor name + Score chip */}
                    <div className="flex items-center justify-between">
                      <span className="text-[14px] font-medium text-text-primary truncate mr-2">
                        {c.vendorName}
                      </span>
                      <span className="tabular font-mono text-[12px] bg-subtle px-1.5 py-0.5 rounded text-text-primary shrink-0">
                        {c.score.toFixed(1)}
                      </span>
                    </div>

                    {/* Row 2: Status + Tier + Awaiting */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant="status" status={c.status} size="sm" />
                      <Badge variant="tier" tier={c.tier} size="sm" />
                      {c.awaitingRole && (
                        <span className="text-[11px] font-medium text-warning bg-warning-subtle px-1.5 py-0.2 rounded">
                          {c.awaitingRole}
                        </span>
                      )}
                    </div>

                    {/* Row 3: Waiting on role duration */}
                    <div className="text-[12px] text-text-tertiary flex items-center gap-1">
                      <Clock size={12} />
                      <span>
                        Waiting on {c.awaitingRole || 'AP'} for {c.waitingSinceHours}h
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Detail Column (60% = 7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            {activeCase ? (
              <div className="rounded-[8px] border border-border bg-surface p-6 space-y-6">
                {/* Header */}
                <div className="flex items-start justify-between pb-4 border-b border-border-subtle">
                  <div>
                    <h3 className="text-[18px] font-semibold text-text-primary tracking-tight">
                      {activeCase.vendorName}
                    </h3>
                    <p className="text-[12px] text-text-secondary mt-0.5 font-mono">
                      {activeCase.id} · Requester: {activeCase.requesterEmail} · {activeCase.country}
                    </p>
                  </div>
                  <Badge variant="status" status={activeCase.status} size="md" />
                </div>

                {/* Counterfactual Card */}
                {activeCase.counterfactual && (
                  <div className="p-3.5 rounded-[6px] bg-subtle/50 border border-border-subtle text-[12px] space-y-1">
                    <div className="font-medium text-text-primary flex items-center gap-1.5">
                      <CheckCircle2 size={14} className="text-success" />
                      <span>Fix {activeCase.counterfactual.itemsCount} items → APPROVED (score {activeCase.counterfactual.targetScore.toFixed(1)})</span>
                    </div>
                    <p className="text-text-secondary">
                      {activeCase.counterfactual.caveat}
                    </p>
                  </div>
                )}

                {/* Blocking Items */}
                <div className="space-y-3">
                  <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
                    Pending Verification Requirements
                  </div>

                  {activeCase.reasonCodes.includes('CALLBACK_REQUIRED') && (
                    <div className="p-3 rounded-[6px] bg-canvas border border-border text-[12px]">
                      <Button
                        size="sm"
                        variant="primary"
                        leftIcon={<PhoneCall size={14} />}
                        onClick={() => {
                          setIsCallbackOpen(true);
                          setCallbackResult(null);
                        }}
                      >
                        Open Callback Desk
                      </Button>
                    </div>
                  )}

                  {activeCase.counterfactual?.blockingItems?.map(b => (
                    <div key={b.number} className="p-3 rounded-[6px] bg-canvas border border-border text-[12px] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-text-primary">{b.title}</span>
                        <Badge size="sm" color={b.severity === 'CRITICAL' ? 'danger' : 'warning'}>{b.severity}</Badge>
                      </div>
                      <p className="text-text-secondary leading-normal">{b.whatYouNeedToDo}</p>
                    </div>
                  ))}
                </div>

                {/* SoD Violation Warning (Inline, non-toast) */}
                {isSoDViolated && (
                  <div
                    role="alert"
                    className="p-3.5 rounded-[6px] bg-danger-subtle border border-danger/30 text-danger text-[12px] flex items-start gap-2.5"
                  >
                    <ShieldAlert size={16} className="shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold">Segregation of Duties Policy Violation</div>
                      <p className="text-danger/90 mt-0.5">
                        You submitted this case ({activeCase.requesterEmail}). Segregation of duties requires a different approver.
                      </p>
                    </div>
                  </div>
                )}

                {/* Action Approval Section */}
                <div className="pt-4 border-t border-border-subtle space-y-4">
                  <Textarea
                    label="Decision Notes (required)"
                    rows={3}
                    placeholder="Document audit rationale and verified credentials…"
                    value={approvalNote}
                    onChange={e => setApprovalNote(e.target.value)}
                  />

                  <Checkbox
                    checked={reviewedFindings}
                    onChange={e => setReviewedFindings(e.target.checked)}
                    label="I have reviewed the automated verification findings and confirm policy compliance."
                  />

                  {/* Sticky Bottom Actions */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <div className="flex items-center gap-2">
                      <Button
                        size="md"
                        variant="ghost"
                        onClick={handleRequestInfo}
                      >
                        Request info
                      </Button>
                      <Button
                        size="md"
                        variant="destructive"
                        onClick={handleReject}
                      >
                        Reject
                      </Button>
                    </div>

                    {/* Approve Button with SoD check */}
                    {isSoDViolated ? (
                      <Tooltip content="You submitted this case. Segregation of duties requires a different approver.">
                        <span className="inline-block">
                          <Button
                            size="md"
                            variant="primary"
                            disabled
                          >
                            Approve
                          </Button>
                        </span>
                      </Tooltip>
                    ) : (
                      <Button
                        size="md"
                        variant="primary"
                        loading={isApproving}
                        disabled={!reviewedFindings || !approvalNote.trim()}
                        onClick={handleApprove}
                      >
                        Approve
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 rounded-[8px] bg-surface border border-border text-center text-text-tertiary">
                Select a case from the queue.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Callback Desk Modal (§7.5) */}
      <Dialog
        isOpen={isCallbackOpen}
        onClose={() => setIsCallbackOpen(false)}
        size="md" // 640px wide per §7.5
        title="Independent Callback Desk"
        description="Verify vendor banking authorization through independent out-of-band telephone verification."
      >
        <div className="space-y-4 text-[13px]">
          {/* Number Dialed */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="font-medium text-text-primary text-[13px]">
                Number dialed
              </label>
              <button
                type="button"
                onClick={() => {
                  setCallbackDialedNumber('+49 30 5551234');
                  setCallbackNumberSource('master');
                }}
                className="text-[11px] text-accent font-medium hover:underline bg-accent-subtle/50 px-2 py-0.5 rounded cursor-pointer"
              >
                Use vendor master number (+49 30 5551234)
              </button>
            </div>
            <Input
              value={callbackDialedNumber}
              aria-label="callback number"
              onChange={e => setCallbackDialedNumber(e.target.value)}
              placeholder="+49 30 5551234"
            />
          </div>

          {/* Number Source Radio */}
          <div className="space-y-2">
            <label className="font-medium text-text-primary block text-[13px]">
              Number source
            </label>
            <div className="grid grid-cols-2 gap-2 text-[12px]">
              {[
                { id: 'master', label: 'Vendor master record' },
                { id: 'registry', label: 'Government registry' },
                { id: 'public', label: 'Public directory' },
                { id: 'request', label: 'From the request form' }
              ].map(opt => (
                <label
                  key={opt.id}
                  className={`p-2.5 rounded-[6px] border flex items-center gap-2 cursor-pointer transition-colors ${
                    callbackNumberSource === opt.id
                      ? opt.id === 'request'
                        ? 'border-danger bg-danger-subtle/30 text-danger'
                        : 'border-accent bg-accent-subtle/40 text-text-primary'
                      : 'border-border bg-surface text-text-secondary'
                  }`}
                >
                  <input
                    type="radio"
                    name="number_source"
                    value={opt.id}
                    checked={callbackNumberSource === opt.id}
                    onChange={() => setCallbackNumberSource(opt.id as any)}
                    className="sr-only"
                  />
                  <span className="font-medium">{opt.label}</span>
                </label>
              ))}
            </div>

            {/* Red Danger Warning if Request number is picked */}
            {callbackNumberSource === 'request' && (
              <div
                role="alert"
                className="p-3 rounded-[6px] bg-danger-subtle border border-danger/40 text-danger text-[12px] flex items-start gap-2"
              >
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <span>
                  This number came from the request. Callbacks must use an independent source to prevent invoice redirect fraud.
                </span>
              </div>
            )}
          </div>

          {/* Outcome Select */}
          <Select
            label="Call outcome"
            value={callbackOutcome}
            onChange={setCallbackOutcome}
            options={[
              { value: 'reached', label: 'Reached — Identity & Bank details confirmed' },
              { value: 'not_reached', label: 'Not reached — Voicemail or line busy' },
              { value: 'wrong_person', label: 'Wrong person — Disavowed authorization' },
              { value: 'refused', label: 'Callback refused' }
            ]}
          />

          {/* Attestation Checkbox */}
          <Checkbox
            checked={callbackAttested}
            onChange={e => setCallbackAttested(e.target.checked)}
            label="I dialed this number myself and verified the identity and bank account routing details."
          />

          {/* Callback Result Box */}
          {callbackResult && (
            <div
              className={`p-3 rounded-[6px] text-[12px] border ${
                callbackResult.success
                  ? 'bg-success-subtle border-success/40 text-success font-medium'
                  : 'bg-danger-subtle border-danger/40 text-danger font-medium'
              }`}
            >
              {callbackResult.message}
            </div>
          )}

          <div className="pt-2 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setIsCallbackOpen(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              disabled={!callbackAttested}
              onClick={handleCallbackSubmit}
            >
              Verify Callback
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
