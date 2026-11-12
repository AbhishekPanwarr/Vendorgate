import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Table, TableColumn } from '../components/primitives/Table';
import { Badge } from '../components/primitives/Badge';
import { Button } from '../components/primitives/Button';
import { Drawer } from '../components/primitives/Drawer';
import { Tabs } from '../components/primitives/Tabs';
import { useApp } from '../context/AppContext';
import { api } from '../api';
import type { VendorMaster } from '../types';
import {
  Users,
  FileText,
  ExternalLink
} from 'lucide-react';

function maskTail(v: string): string {
  const d = v.replace(/\D/g, '');
  if (d.length <= 4) return v || '—';
  return `••••${d.slice(-4)}`;
}

export const VendorsPage: React.FC = () => {
  const { navigate, addToast } = useApp();
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState('ALL');
  const [selectedVendor, setSelectedVendor] = useState<VendorMaster | null>(null);
  const [vendors, setVendors] = useState<VendorMaster[]>([]);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const rows = await api.getVendors();
        const mapped: VendorMaster[] = await Promise.all(rows.map(async (row) => {
          const r = row as Record<string, unknown>;
          const caseId = String(r.case_id ?? '');
          let legal = String(r.vendor_id ?? caseId);
          let country = '', tier = 'LOW', status = 'PENDING', score = 0;
          let contactName = '', contactEmail = '', phone = '', address = '';
          let owners: { name: string; percentage: number; role: string }[] = [];
          let hasBankChange = false;
          let taxId = '';
          try {
            const c = await api.getCase(caseId);
            const run = (c as Record<string, unknown>).run as Record<string, unknown> | undefined;
            const payload = ((run?.payload ?? {}) as Record<string, unknown>);
            const company = (payload.company ?? {}) as Record<string, unknown>;
            const contact = (company.primary_contact ?? {}) as Record<string, unknown>;
            const ap = (company.ap_contact ?? {}) as Record<string, unknown>;
            const srequester = (payload.requester ?? {}) as Record<string, unknown>;
            legal = String(company.legal_name ?? legal);
            country = String(company.country ?? '');
            const addr = (company.registered_address ?? {}) as Record<string, unknown>;
            address = [addr.line1, addr.city, addr.region, addr.postal_code].filter(Boolean).join(', ');
            contactName = String(contact.name ?? '');
            contactEmail = String(contact.email ?? ap.email ?? srequester.email ?? '');
            phone = String(contact.phone ?? '');
            const tax = (payload.tax ?? {}) as Record<string, unknown>;
            taxId = String(tax.tax_id ?? '');
            owners = (Array.isArray(company.owners) ? company.owners : []).map(o => {
              const oo = o as Record<string, unknown>;
              return { name: String(oo.name ?? ''), percentage: Number(oo.ownership_pct ?? 0), role: String(oo.role ?? '') };
            });
            hasBankChange = String(payload.submission_type) === 'CHANGE_REQUEST';
            const dec = (run?.decision ?? {}) as Record<string, unknown>;
            status = String(dec.status ?? (c as Record<string, unknown>).status ?? 'PENDING');
            tier = String(dec.tier ?? (c as Record<string, unknown>).tier ?? 'LOW');
            const sc = (dec.score ?? {}) as Record<string, unknown>;
            score = Number(sc.total ?? 0);
          } catch { /* keep row-level fallbacks */ }
          return {
            id: String(r.vendor_id ?? caseId), name: legal, taxIdMasked: maskTail(taxId),
            country, tier: tier as VendorMaster['tier'], status: status as VendorMaster['status'],
            createdAt: '', lastVerifiedAt: '', hasBankChange,
            contactName, contactEmail, address, masterPhone: phone, owners,
            scoreHistory: [score], associatedCases: caseId ? [caseId] : [],
          };
        }));
        if (live) setVendors(mapped);
      } catch {
        if (live) addToast({ title: 'Vendors unavailable', description: 'Server unreachable.', variant: 'danger' });
      }
    })();
    return () => { live = false; };
  }, [addToast]);

  // Detail Drawer state
  const [drawerTab, setDrawerTab] = useState('overview');

  const filteredVendors = vendors.filter(v => {
    if (tierFilter !== 'ALL' && v.tier !== tierFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        v.name.toLowerCase().includes(q) ||
        v.id.toLowerCase().includes(q) ||
        v.country.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const columns: TableColumn<VendorMaster>[] = [
    {
      key: 'name',
      header: 'Vendor',
      render: v => (
        <div className="flex items-center gap-2">
          <span className="font-semibold text-text-primary">{v.name}</span>
          <span className="font-mono text-[11px] text-text-tertiary">({v.id})</span>
        </div>
      )
    },
    {
      key: 'taxIdMasked',
      header: 'Tax ID',
      render: v => <span className="font-mono text-[12px] text-text-secondary">{v.taxIdMasked}</span>,
      width: '100px'
    },
    {
      key: 'country',
      header: 'Country',
      render: v => <span className="text-[12px] font-medium text-text-primary">{v.country}</span>,
      width: '80px'
    },
    {
      key: 'tier',
      header: 'Tier',
      render: v => <Badge variant="tier" tier={v.tier} size="sm" />,
      width: '100px'
    },
    {
      key: 'status',
      header: 'Status',
      render: v => <Badge variant="status" status={v.status} size="sm" />,
      width: '110px'
    },
    {
      key: 'createdAt',
      header: 'Created',
      render: v => <span className="text-[12px] text-text-tertiary tabular">{v.createdAt}</span>,
      width: '100px'
    },
    {
      key: 'lastVerifiedAt',
      header: 'Last Verified',
      render: v => <span className="text-[12px] text-text-tertiary tabular">{v.lastVerifiedAt}</span>,
      width: '110px'
    },
    {
      key: 'actions',
      header: 'Actions',
      render: v => (
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedVendor(v);
          }}
        >
          View detail →
        </Button>
      ),
      align: 'right',
      width: '120px'
    }
  ];

  return (
    <div className="space-y-6 animate-in fade-in-0 duration-240">
      <PageHeader
        title="Vendor Directory"
        description="Master vendor repository, compliance status, and shared attribute network intelligence."
        actions={
          <div className="flex items-center gap-2">
            {/* Segmented Control */}
            <div className="flex items-center bg-subtle p-0.5 rounded-[6px] border border-border">
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`h-7 px-3 rounded-[4px] text-[12px] font-medium transition-colors cursor-pointer ${
                  viewMode === 'table' ? 'bg-surface text-text-primary shadow-xs' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                Table
              </button>
              <button
                type="button"
                onClick={() => setViewMode('graph')}
                className={`h-7 px-3 rounded-[4px] text-[12px] font-medium transition-colors cursor-pointer ${
                  viewMode === 'graph' ? 'bg-surface text-text-primary shadow-xs' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                Graph
              </button>
            </div>
          </div>
        }
      />

      {viewMode === 'table' ? (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <input
              type="text"
              placeholder="Search vendor name, ID, country…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="h-9 px-3 rounded-[6px] border border-border bg-surface text-[13px] w-72 focus-ring"
            />

            <div className="flex items-center gap-1.5">
              <span className="text-[12px] text-text-secondary">Tier:</span>
              {['ALL', 'LOW', 'MEDIUM', 'HIGH'].map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTierFilter(t)}
                  className={`h-7 px-2.5 rounded-[4px] text-[11px] font-medium transition-colors ${
                    tierFilter === t ? 'bg-accent text-white' : 'bg-subtle text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <Table
            columns={columns}
            data={filteredVendors}
            rowKey={v => v.id}
            onRowClick={v => setSelectedVendor(v)}
            emptyState={
              <div className="p-8 text-center space-y-2">
                <Users size={24} className="text-text-tertiary mx-auto stroke-[1.5]" />
                <p className="text-[14px] font-medium text-text-primary">No vendors found.</p>
                <p className="text-[12px] text-text-secondary">Approved vendors and active onboardings appear here.</p>
              </div>
            }
          />
        </div>
      ) : (
        /* Graph Mode */
        <div className="space-y-4">
            <div className="p-4 rounded-[8px] bg-muted border border-border flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
            <div className="text-[13px] text-text-primary">
              <span className="font-semibold">Master Relationship Graph</span>
              <p className="text-[12px] text-text-secondary">Vendors from the live registry. Flagged = non-approved status.</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase font-mono text-text-tertiary">Filter:</span>
              <Badge size="sm" color="danger">Flagged ({vendors.filter(v => v.status !== 'APPROVED').length})</Badge>
              <Badge size="sm" color="neutral">{vendors.length} total</Badge>
            </div>
          </div>

          <div className="relative min-h-[500px] rounded-[8px] border border-border bg-muted overflow-hidden flex items-center justify-center p-8">
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {vendors.slice(0, 6).map((_, i, arr) => i === 0 ? null : (
                <line key={i} x1={`${15 + (i - 1) * 14}%`} y1="45%" x2={`${15 + i * 14}%`} y2="45%"
                  stroke="var(--border-strong)" strokeWidth="1.5" />
              ))}
            </svg>

            {/* Nodes */}
            {vendors.slice(0, 6).map((v, i) => {
              const left = 8 + i * 15;
              const top = i % 2 === 0 ? 32 : 58;
              const flagged = v.status !== 'APPROVED';
              return (
                <div
                  key={v.id}
                  onClick={() => setSelectedVendor(v)}
                  className={`absolute p-3.5 bg-surface border-2 rounded-[6px] shadow-sm w-44 text-center cursor-pointer hover:border-accent ${flagged ? 'border-danger' : 'border-border'}`}
                  style={{ left: `${left}%`, top: `${top}%` }}
                >
                  <div className="text-[13px] font-semibold text-text-primary truncate">{v.name}</div>
                  <Badge size="sm" color={v.status === 'APPROVED' ? 'success' : v.status === 'PENDING' ? 'warning' : 'danger'} className="mt-1">{v.status}</Badge>
                </div>
              );
            })}
            {vendors.length === 0 && (
              <p className="text-[13px] text-text-secondary">No vendors in registry yet — submit one to populate the graph.</p>
            )}

            {/* Legend in bottom-left */}
            <div className="absolute bottom-4 left-4 p-3 rounded-[6px] bg-surface/90 border border-border-subtle text-[11px] space-y-1.5 backdrop-blur">
              <div className="font-semibold text-text-primary uppercase text-[10px]">Legend</div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-2 rounded bg-surface border border-border inline-block" />
                <span className="text-text-secondary">Vendor Entity</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-danger-subtle border border-danger inline-block" />
                <span className="text-text-secondary">Flagged Attribute</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-subtle border border-border inline-block" />
                <span className="text-text-secondary">Shared Infrastructure</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Vendor Detail Drawer (640px wide per §7.6) */}
      <Drawer
        isOpen={!!selectedVendor}
        onClose={() => setSelectedVendor(null)}
        width="wide"
        title={selectedVendor?.name}
        subtitle={`${selectedVendor?.id} · ${selectedVendor?.country}`}
        headerActions={
          selectedVendor && (
            <div className="flex items-center gap-1.5">
              <Badge variant="status" status={selectedVendor.status} size="sm" />
              <Badge variant="tier" tier={selectedVendor.tier} size="sm" />
            </div>
          )
        }
      >
        {selectedVendor && (
          <div className="space-y-6">
            <Tabs
              tabs={[
                { id: 'overview', label: 'Overview' },
                { id: 'cases', label: `Cases (${selectedVendor.associatedCases.length})` },
                { id: 'bank', label: 'Bank Details' }
              ]}
              activeTab={drawerTab}
              onChange={setDrawerTab}
            />

            {drawerTab === 'overview' && (
              <div className="space-y-6 text-[13px]">
                {/* Score sparkline */}
                <div className="p-4 rounded-[8px] bg-subtle/50 border border-border-subtle space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] font-medium text-text-secondary">Historical Risk Score (Last 10 cases)</span>
                    <span className="font-mono text-[12px] font-semibold text-text-primary">
                      Current: {selectedVendor.scoreHistory[selectedVendor.scoreHistory.length - 1]}
                    </span>
                  </div>

                  {/* SVG Sparkline */}
                  <div className="h-12 w-full flex items-end">
                    <svg className="w-full h-10 overflow-visible">
                      <polyline
                        fill="none"
                        stroke="var(--accent)"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={selectedVendor.scoreHistory
                          .map((val, idx) => {
                            const x = (idx / (selectedVendor.scoreHistory.length - 1 || 1)) * 520;
                            const y = 40 - (val / 100) * 35;
                            return `${x},${y}`;
                          })
                          .join(' ')}
                      />
                      {/* Last dot */}
                      {selectedVendor.scoreHistory.length > 0 && (
                        <circle
                          cx="520"
                          cy={40 - (selectedVendor.scoreHistory[selectedVendor.scoreHistory.length - 1] / 100) * 35}
                          r="4"
                          fill="var(--accent)"
                        />
                      )}
                    </svg>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary">
                    Contact & Headquarters
                  </h4>
                  <div className="grid grid-cols-2 gap-3 p-3.5 rounded-[6px] bg-surface border border-border text-[12px]">
                    <div>Contact: <span className="font-medium text-text-primary">{selectedVendor.contactName}</span></div>
                    <div>Email: <span className="font-medium text-text-primary">{selectedVendor.contactEmail}</span></div>
                    <div>Master Phone: <span className="font-mono text-text-primary">{selectedVendor.masterPhone}</span></div>
                    <div>Address: <span className="font-medium text-text-primary">{selectedVendor.address}</span></div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary">
                    Beneficial Owners
                  </h4>
                  <div className="space-y-2">
                    {selectedVendor.owners.map((owner, idx) => (
                      <div key={idx} className="p-3 rounded-[6px] bg-surface border border-border flex justify-between items-center text-[12px]">
                        <div>
                          <span className="font-medium text-text-primary">{owner.name}</span>
                          <span className="text-text-tertiary ml-2">({owner.role})</span>
                        </div>
                        <span className="tabular font-mono text-accent font-semibold">{owner.percentage}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {drawerTab === 'cases' && (
              <div className="space-y-2">
                {selectedVendor.associatedCases.map(cId => (
                  <div
                    key={cId}
                    onClick={() => {
                      navigate(`/cases/${cId}`);
                      setSelectedVendor(null);
                    }}
                    className="p-3.5 rounded-[6px] border border-border bg-surface hover:bg-subtle flex items-center justify-between text-[13px] cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <FileText size={16} className="text-accent" />
                      <span className="font-mono font-medium text-text-primary">{cId}</span>
                    </div>
                    <span className="text-[12px] text-accent flex items-center gap-1">
                      <span>View case</span>
                      <ExternalLink size={12} />
                    </span>
                  </div>
                ))}
              </div>
            )}

            {drawerTab === 'bank' && (
              <div className="p-4 rounded-[6px] bg-subtle/50 border border-border-subtle space-y-2 text-[13px]">
                <div>Masked Disbursement Account: <span className="font-mono font-semibold text-text-primary">{selectedVendor.taxIdMasked}</span></div>
                <div>Bank Change History: <span className="font-medium">{selectedVendor.hasBankChange ? 'Altered in last onboarding' : 'No recent alterations'}</span></div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};
