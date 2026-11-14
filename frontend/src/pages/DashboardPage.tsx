import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Table, TableColumn } from '../components/primitives/Table';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { useApp } from '../context/AppContext';
import { api } from '../api';
import type { RunRecord } from '../types';
import { Plus, Zap, ChevronRight, ChevronDown, Clock, TrendingUp } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { runs, cases, navigate } = useApp();
  const [impactOpen, setImpactOpen] = useState(false);
  const [reasonCodes, setReasonCodes] = useState<{ code: string; label: string; count: number; pct: number }[]>([]);

  // Distribution counts (live)
  const approvedCount = cases.filter(c => c.status === 'APPROVED').length;
  const pendingCount = cases.filter(c => c.status === 'PENDING').length;
  const rejectedCount = cases.filter(c => c.status === 'REJECTED').length;
  const totalCases = cases.length || 1;
  const totalRuns = runs.length || 1;
  const autoRate = approvedCount / totalCases;

  // Editable impact model assumptions
  const [vendorVolume, setVendorVolume] = useState(120); // vendors/month
  const [manualMinutesPerCase, setManualMinutesPerCase] = useState(45); // min manual triage
  const [chaseCyclesPerVendor, setChaseCyclesPerVendor] = useState(2.4);

  // Impact calculations (explicit planning assumptions, not measured data)
  const automatedVendors = Math.round(vendorVolume * autoRate);
  const hoursSavedPerMonth = Math.round((automatedVendors * manualMinutesPerCase) / 60);
  const chaseCyclesAvoided = Math.round(automatedVendors * chaseCyclesPerVendor);

  // Runs Table Columns
  const columns: TableColumn<RunRecord>[] = [
    {
      key: 'submittedAt',
      header: 'Time',
      render: r => <span className="text-text-secondary font-mono text-[12px]">{r.submittedAt.split(' ')[1] || r.submittedAt}</span>,
      width: '90px'
    },
    {
      key: 'vendorName',
      header: 'Vendor',
      render: r => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-text-primary">{r.vendorName}</span>
          <span className="font-mono text-[11px] text-text-tertiary">({r.id})</span>
        </div>
      )
    },
    {
      key: 'mode',
      header: 'Mode',
      render: r => (
        <span className="text-[12px] text-text-secondary font-mono uppercase bg-subtle px-1.5 py-0.5 rounded">
          {r.mode}
        </span>
      ),
      width: '100px'
    },
    {
      key: 'status',
      header: 'Status',
      render: r => <Badge variant="status" status={r.status} size="sm" />,
      width: '110px'
    },
    {
      key: 'tier',
      header: 'Tier',
      render: r => <Badge variant="tier" tier={r.tier} size="sm" />,
      width: '100px'
    },
    {
      key: 'score',
      header: 'Score',
      render: r => <span className="tabular font-medium text-text-primary">{r.score.toFixed(1)}</span>,
      numeric: true,
      width: '70px'
    },
    {
      key: 'durationMs',
      header: 'Duration',
      render: r => <span className="tabular text-text-secondary text-[12px]">{r.durationMs}ms</span>,
      numeric: true,
      width: '85px'
    },
    {
      key: 'cached',
      header: 'Cached',
      render: r => r.cached ? (
        <span className="inline-flex items-center text-accent" title="Cached pipeline pass">
          <Zap size={14} className="fill-accent" />
        </span>
      ) : (
        <span className="text-text-tertiary">—</span>
      ),
      align: 'center',
      width: '60px'
    }
  ];

  // Top blocking reasons computed from live case reason codes
  useEffect(() => {
    let live = true;
    api.getCases().then(rows => {
      if (!live) return;
      const counts = new Map<string, number>();
      let total = 0;
      for (const row of rows) {
        const codes = Array.isArray((row as Record<string, unknown>).reason_codes)
          ? ((row as Record<string, unknown>).reason_codes as string[])
          : [];
        if (codes.length === 0) continue;
        total += 1;
        for (const c of new Set(codes)) counts.set(c, (counts.get(c) ?? 0) + 1);
      }
      const pretty: Record<string, string> = {
        NAME_MISMATCH_BANK: 'Bank holder ↔ legal name',
        ROUTING_CHECKSUM_INVALID: 'Routing checksum invalid',
        TAX_FORMAT_INVALID: 'Tax ID format invalid',
        SANCTIONS_MATCH: 'Sanctions list match',
        DUPLICATE_EXISTING: 'Duplicate of existing vendor',
      };
      const top = [...counts.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([code, count]) => ({
          code,
          label: pretty[code] ?? code,
          count,
          pct: total > 0 ? Math.round((count / Math.max(1, rows.length)) * 100) : 0,
        }));
      setReasonCodes(top);
    }).catch(() => {});
    return () => { live = false; };
  }, []);

  // Distribution counts are declared above (live from context).

  // Donut SVG circumference calculation
  const radius = 64;
  const strokeWidth = 12;
  const circumference = 2 * Math.PI * radius; // ~402.12
  const approvedOffset = 0;
  const approvedDash = (approvedCount / totalCases) * circumference;
  const pendingOffset = -approvedDash;
  const pendingDash = (pendingCount / totalCases) * circumference;
  const rejectedOffset = -(approvedDash + pendingDash);
  const rejectedDash = (rejectedCount / totalCases) * circumference;

  // Cases by country (real distribution for the histogram visual)
  const countryBuckets = ['US', 'IN', 'GB', 'DE'].map(c => ({
    bin: c,
    count: cases.filter(x => x.country === c).length,
  }));
  const countryMax = Math.max(1, ...countryBuckets.map(b => b.count));

  return (
    <div className="space-y-8 animate-in fade-in-0 duration-240">
      <PageHeader
        title="Dashboard"
        description="Live operational telemetry, decision throughput, and verification queues."
        actions={
          <Button
            variant="primary"
            leftIcon={<Plus size={16} />}
            onClick={() => navigate('/submit')}
          >
            Submit vendor
          </Button>
        }
      />

      {/* Row 1: 6 KPI Tiles in 6-col grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Tile 1 */}
        <div className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Total Runs
          </div>
          <div className="text-[30px] font-semibold text-text-primary tabular tracking-[-0.02em] my-1">
            {runs.length}
          </div>
          <div className="text-[12px] text-text-tertiary">
            {cases.length} cases in store
          </div>
        </div>

        {/* Tile 2 */}
        <div className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Auto-approve rate
          </div>
          <div className="text-[30px] font-semibold text-text-primary tabular tracking-[-0.02em] my-1">
            {(autoRate * 100).toFixed(1)}%
          </div>
          <div className="text-[12px] text-success flex items-center gap-0.5">
            <TrendingUp size={12} /> of triaged cases
          </div>
        </div>

        {/* Tile 3 */}
        <div className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            First-pass yield
          </div>
          <div className="text-[30px] font-semibold text-text-primary tabular tracking-[-0.02em] my-1">
            {(autoRate * 100).toFixed(1)}%
          </div>
          <div className="text-[12px] text-text-tertiary">
            Share approved first pass
          </div>
        </div>

        {/* Tile 4 */}
        <div className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Pending triage
          </div>
          <div className="text-[30px] font-semibold text-text-primary tabular tracking-[-0.02em] my-1">
            {pendingCount}
          </div>
          <div className="text-[12px] text-text-tertiary">
            cases open now
          </div>
        </div>

        {/* Tile 5 */}
        <div className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Rejected
          </div>
          <div className="text-[30px] font-semibold text-text-primary tabular tracking-[-0.02em] my-1">
            {rejectedCount}
          </div>
          <div className="text-[12px] text-text-tertiary">
            blocked decisions
          </div>
        </div>

        {/* Tile 6 */}
        <div className="p-5 rounded-[8px] bg-surface border border-border flex flex-col justify-between">
          <div className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
            Critical catches
          </div>
          <div className="text-[30px] font-semibold text-success tabular tracking-[-0.02em] my-1">
            0 / 109
          </div>
          <div className="text-[12px] text-success">
            frozen test split E1
          </div>
        </div>
      </div>

      {/* Row 2: 2-col (60% / 40%, gap 24px) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (60% = 7 cols on 12-col grid) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em]">
              Recent Pipeline Runs
            </h2>
            <span className="text-[12px] text-text-secondary">
              Showing {runs.length} runs
            </span>
          </div>

          <Table
            columns={columns}
            data={runs}
            rowKey={r => r.id}
            compact
            onRowClick={r => navigate(`/cases/${r.caseId}`)}
            emptyState={
              <div className="p-8 text-center space-y-3">
                <Clock size={28} className="text-text-tertiary mx-auto stroke-[1.5]" />
                <p className="text-[14px] font-medium text-text-primary">No runs yet.</p>
                <p className="text-[12px] text-text-secondary">Submit your first vendor to initiate the 13-stage verification pipeline.</p>
                <Button size="sm" variant="primary" onClick={() => navigate('/submit')}>
                  Submit your first vendor →
                </Button>
              </div>
            }
          />
        </div>

        {/* Right Column (40% = 5 cols) - Stacked Charts */}
        <div className="lg:col-span-5 space-y-4">
          {/* Chart 1: Status Distribution Donut */}
          <Card padding="compact" title="Decision Distribution">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pt-2">
              {/* Donut graphic */}
              <div className="relative w-40 h-40 flex items-center justify-center shrink-0">
                <svg width="160" height="160" viewBox="0 0 160 160" className="transform -rotate-90">
                  {/* Background Track */}
                  <circle
                    cx="80"
                    cy="80"
                    r={radius}
                    fill="transparent"
                    stroke="var(--bg-subtle)"
                    strokeWidth={strokeWidth}
                  />
                  {/* Approved segment */}
                  {approvedDash > 0 && (
                    <circle
                      cx="80"
                      cy="80"
                      r={radius}
                      fill="transparent"
                      stroke="var(--success)"
                      strokeWidth={strokeWidth}
                      strokeDasharray={`${approvedDash} ${circumference}`}
                      strokeDashoffset={approvedOffset}
                      className="transition-all duration-600 ease-out"
                    />
                  )}
                  {/* Pending segment */}
                  {pendingDash > 0 && (
                    <circle
                      cx="80"
                      cy="80"
                      r={radius}
                      fill="transparent"
                      stroke="var(--warning)"
                      strokeWidth={strokeWidth}
                      strokeDasharray={`${pendingDash} ${circumference}`}
                      strokeDashoffset={pendingOffset}
                      className="transition-all duration-600 ease-out"
                    />
                  )}
                  {/* Rejected segment */}
                  {rejectedDash > 0 && (
                    <circle
                      cx="80"
                      cy="80"
                      r={radius}
                      fill="transparent"
                      stroke="var(--danger)"
                      strokeWidth={strokeWidth}
                      strokeDasharray={`${rejectedDash} ${circumference}`}
                      strokeDashoffset={rejectedOffset}
                      className="transition-all duration-600 ease-out"
                    />
                  )}
                </svg>
                {/* Center total count */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-[24px] font-semibold text-text-primary tabular tracking-tight">
                    {runs.length}
                  </span>
                  <span className="text-[11px] uppercase tracking-[0.04em] text-text-tertiary">
                    Decisions
                  </span>
                </div>
              </div>

              {/* Legend with tabular counts */}
              <div className="space-y-2 w-full text-[13px]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-success shrink-0" />
                    <span className="text-text-primary">Approved</span>
                  </div>
                  <span className="tabular font-medium text-text-primary">
                    {approvedCount} ({Math.round((approvedCount / totalCases) * 100)}%)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-warning shrink-0" />
                    <span className="text-text-primary">Pending</span>
                  </div>
                  <span className="tabular font-medium text-text-primary">
                    {pendingCount} ({Math.round((pendingCount / totalCases) * 100)}%)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-danger shrink-0" />
                    <span className="text-text-primary">Rejected</span>
                  </div>
                  <span className="tabular font-medium text-text-primary">
                    {rejectedCount} ({Math.round((rejectedCount / totalCases) * 100)}%)
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Chart 2: Top Reason Codes Horizontal Bars */}
          <Card padding="compact" title="Top Blocking Reasons">
            <div className="space-y-3 pt-2">
              {reasonCodes.map(item => (
                <div key={item.code} className="space-y-1">
                  <div className="flex items-center justify-between text-[12px]">
                    <span className="font-medium text-text-primary truncate mr-2" title={item.label}>
                      {item.label}
                    </span>
                    <span className="tabular text-text-secondary shrink-0 font-mono">
                      {item.count} cases ({item.pct}%)
                    </span>
                  </div>
                  <div className="h-2 w-full bg-subtle rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all duration-360 ease-out"
                      style={{ width: `${item.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Chart 3: Cases by jurisdiction */}
          <Card padding="compact" title="Cases by Jurisdiction">
            <div className="pt-2">
              <div className="grid grid-cols-4 gap-3 items-end h-28 border-b border-border-subtle pb-2">
                {countryBuckets.map(bin => (
                  <div key={bin.bin} className="flex flex-col items-center gap-1.5 h-full justify-end">
                    <span className="text-[11px] font-mono text-text-primary tabular">
                      {bin.count}
                    </span>
                    <div
                      className="w-full bg-warning/80 hover:bg-warning rounded-t-[4px] transition-all duration-240"
                      style={{ height: `${Math.round((bin.count / countryMax) * 100)}%` }}
                    />
                    <span className="text-[11px] text-text-tertiary">
                      {bin.bin}
                    </span>
                  </div>
                ))}
              </div>
              <div className="text-[11px] text-text-tertiary text-center mt-2">
                Supported jurisdictions: US · IN · GB · DE
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Row 3: Collapsible Impact Model Card */}
      <div className="rounded-[8px] border border-border bg-surface overflow-hidden">
        <button
          type="button"
          onClick={() => setImpactOpen(!impactOpen)}
          className="w-full p-4 px-5 flex items-center justify-between text-left hover:bg-subtle transition-colors cursor-pointer select-none"
        >
          <div className="flex items-center gap-2.5">
            <span className="text-text-tertiary">
              {impactOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </span>
            <span className="text-[14px] font-semibold text-text-primary">
              Operational Impact & Hours Saved Model
            </span>
          </div>
          <span className="text-[12px] text-accent font-medium tabular">
            Estimated ~{hoursSavedPerMonth} hours/mo saved
          </span>
        </button>

        {impactOpen && (
          <div className="p-6 pt-2 border-t border-border-subtle bg-subtle/20 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="text-[12px] font-medium text-text-primary block mb-1">
                  Monthly Vendor Intake Volume
                </label>
                <input
                  type="number"
                  value={vendorVolume}
                  onChange={e => setVendorVolume(Number(e.target.value) || 0)}
                  className="h-8 w-full rounded-[4px] border border-border bg-surface px-2.5 text-[13px] tabular focus-ring"
                />
                <span className="text-[11px] text-text-tertiary mt-1 block">Expected submissions / month</span>
              </div>

              <div>
                <label className="text-[12px] font-medium text-text-primary block mb-1">
                  Manual AP Triage per Vendor (min)
                </label>
                <input
                  type="number"
                  value={manualMinutesPerCase}
                  onChange={e => setManualMinutesPerCase(Number(e.target.value) || 0)}
                  className="h-8 w-full rounded-[4px] border border-border bg-surface px-2.5 text-[13px] tabular focus-ring"
                />
                <span className="text-[11px] text-text-tertiary mt-1 block">Baseline human review minutes</span>
              </div>

              <div>
                <label className="text-[12px] font-medium text-text-primary block mb-1">
                  Chase Cycles per Non-Verified Vendor
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={chaseCyclesPerVendor}
                  onChange={e => setChaseCyclesPerVendor(Number(e.target.value) || 0)}
                  className="h-8 w-full rounded-[4px] border border-border bg-surface px-2.5 text-[13px] tabular focus-ring"
                />
                <span className="text-[11px] text-text-tertiary mt-1 block">Back-and-forth email interactions</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-[6px] bg-surface border border-border-subtle text-center">
              <div>
                <span className="text-[11px] text-text-tertiary uppercase block">Auto-Approved Cases</span>
                <span className="text-[20px] font-semibold text-text-primary tabular">{automatedVendors} / mo</span>
              </div>
              <div>
                <span className="text-[11px] text-text-tertiary uppercase block">Analyst Hours Saved</span>
                <span className="text-[20px] font-semibold text-success tabular">{hoursSavedPerMonth} hrs / mo</span>
              </div>
              <div>
                <span className="text-[11px] text-text-tertiary uppercase block">Avoided Chase Loops</span>
                <span className="text-[20px] font-semibold text-text-primary tabular">{chaseCyclesAvoided} loops</span>
              </div>
              <div>
                <span className="text-[11px] text-text-tertiary uppercase block">Annualized Capacity</span>
                <span className="text-[20px] font-semibold text-accent tabular font-mono">
                  ${Math.round(hoursSavedPerMonth * 12 * 65).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
