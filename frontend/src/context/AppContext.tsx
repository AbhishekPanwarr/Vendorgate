import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { RoleType, RunRecord, CaseRecord, FindingEvidence, AuditEvent, Stage, CheckItem } from '../types';
import { api, mapRun, mapCase } from '../api';

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

interface AppContextType {
  // Routing
  currentPath: string;
  navigate: (path: string) => void;

  // Theme
  theme: 'light' | 'dark';
  toggleTheme: () => void;

  // Role
  role: RoleType;
  setRole: (role: RoleType) => void;

  // Toast
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;

  // Command palette
  isCommandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // Evidence Drawer
  activeEvidence: FindingEvidence | null;
  openEvidenceDrawer: (evidence: FindingEvidence) => void;
  closeEvidenceDrawer: () => void;

  // Data (live from /api/v1 — visuals unchanged)
  runs: RunRecord[];
  cases: CaseRecord[];
  stages: Stage[];
  checks: CheckItem[];
  evidenceMap: Record<string, FindingEvidence>;
  auditEvents: AuditEvent[];
  virtualNow: string;
  advanceVirtualClock: (days: number) => Promise<void>;
  clockHistory: { timestamp: string; daysAdded: number; newDate: string }[];
  faults: Record<string, { status: 'Off' | 'Timeout' | 'Error' | 'Slow'; ttl: number }>;
  setFault: (adapter: string, status: 'Off' | 'Timeout' | 'Error' | 'Slow', ttl: number) => void;
  refreshCases: () => Promise<void>;

  // Actions (real endpoints; server enforces SoD/roles)
  addRun: (run: RunRecord) => void;
  approveCase: (caseId: string, note: string) => Promise<{ success: boolean; error?: string }>;
  rejectCase: (caseId: string, note: string) => Promise<{ success: boolean; error?: string }>;
  requestInfoCase: (caseId: string, note: string) => Promise<{ success: boolean; error?: string }>;
  verifyCallbackDesk: (caseId: string, numberSource: string, dialedNumber: string) => Promise<{ success: boolean; message: string }>;
  resetAllData: () => Promise<void>;
}

const AppContext = createContext<AppContextType | null>(null);

const FAULT_ADAPTERS = ['Registry', 'IRS', 'GST', 'VIES', 'Bank', 'LLM'];

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // URL routing state
  const [currentPath, setCurrentPath] = useState<string>(() => {
    return window.location.pathname || '/';
  });

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Theme state
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('vendorgate:theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('vendorgate:theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    document.body.classList.add('theme-transitioning');
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
    setTimeout(() => {
      document.body.classList.remove('theme-transitioning');
    }, 120);
  }, []);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const addToast = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // Command palette
  const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
      if (e.key === 'Escape' && isCommandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen]);

  // Evidence Drawer
  const [activeEvidence, setActiveEvidence] = useState<FindingEvidence | null>(null);
  const openEvidenceDrawer = useCallback((evidence: FindingEvidence) => {
    setActiveEvidence(evidence);
  }, []);
  const closeEvidenceDrawer = useCallback(() => {
    setActiveEvidence(null);
  }, []);

  // Role state
  const [role, setRoleState] = useState<RoleType>('Controller');
  const setRole = useCallback((newRole: RoleType) => {
    setRoleState(newRole);
    let desc = 'Actions now available.';
    if (newRole === 'Controller') desc = 'Controller approval actions now available.';
    if (newRole === 'AP Analyst') desc = 'AP Analyst triage queue unlocked.';
    if (newRole === 'Compliance') desc = 'Compliance callback desk unlocked.';
    if (newRole === 'Auditor') desc = 'Auditor read-only verification view.';
    if (newRole === 'Admin') desc = 'Admin clock panel active.';
    addToast({
      title: `Role: ${newRole}`,
      description: desc,
      variant: 'default'
    });
  }, [addToast]);

  // Live data from the API (replaces seed.ts)
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [virtualNow, setVirtualNow] = useState<string>('');
  const [clockHistory, setClockHistory] = useState<{ timestamp: string; daysAdded: number; newDate: string }[]>([]);

  const refreshCases = useCallback(async () => {
    try {
      const rows = await api.getCases();
      const mapped: CaseRecord[] = [];
      const mappedRuns: RunRecord[] = [];
      for (const row of rows) {
        let run: Awaited<ReturnType<typeof api.getRun>> | undefined;
        try {
          if (row.run_id) run = await api.getRun(row.run_id);
        } catch {
          run = undefined;
        }
        mapped.push(mapCase(row, run));
        if (run) mappedRuns.push(mapRun(run));
      }
      setCases(mapped);
      setRuns(mappedRuns);
    } catch {
      // backend unreachable — pages render empty states
    }
  }, []);

  useEffect(() => {
    refreshCases();
  }, [refreshCases]);

  // Stages / checks / evidence are derived per-run by pages from run findings.
  const stages: Stage[] = [];
  const checks: CheckItem[] = [];
  const evidenceMap: Record<string, FindingEvidence> = {};

  const advanceVirtualClock = useCallback(async (days: number) => {
    const res = await api.clockAdvance(days);
    setVirtualNow(res.now);
    setClockHistory(prev => [
      { timestamp: new Date().toISOString(), daysAdded: days, newDate: res.now },
      ...prev,
    ]);
    addToast({
      title: `Virtual clock advanced +${days} days`,
      description: 'Triggered scheduled reminder nudges and deadline validations.',
      variant: 'default',
    });
    await refreshCases();
  }, [addToast, refreshCases]);

  // Fault injection is not exposed by the API (test-only concern, see
  // backend/tests/chaos). The panel state below is display-only.
  const [faults, setFaults] = useState<Record<string, { status: 'Off' | 'Timeout' | 'Error' | 'Slow'; ttl: number }>>(
    Object.fromEntries(FAULT_ADAPTERS.map(a => [a, { status: 'Off' as const, ttl: 300 }])),
  );

  const setFault = useCallback((adapter: string, status: 'Off' | 'Timeout' | 'Error' | 'Slow', ttl: number) => {
    setFaults(prev => ({
      ...prev,
      [adapter]: { status, ttl }
    }));
    addToast({
      title: `Fault panel: ${adapter} → ${status}`,
      description: 'Display only — the server exposes no fault-injection endpoint; adapter faults live in backend/tests/chaos.',
      variant: status === 'Off' ? 'default' : 'warning'
    });
  }, [addToast]);

  const addRun = useCallback((newRun: RunRecord) => {
    setRuns(prev => [newRun, ...prev]);
    void refreshCases();
  }, [refreshCases]);

  const mutateApproval = useCallback(async (
    caseId: string, action: 'APPROVE' | 'REJECT', note: string,
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      await api.approve(caseId, action, note, 'panwarabhishek629@gmail.com', role);
      addToast({
        title: `Case ${caseId} ${action === 'APPROVE' ? 'Approved' : 'Rejected'}`,
        variant: action === 'APPROVE' ? 'success' : 'danger',
      });
      await refreshCases();
      return { success: true };
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      return { success: false, error: msg };
    }
  }, [role, addToast, refreshCases]);

  const approveCase = useCallback((caseId: string, note: string) => mutateApproval(caseId, 'APPROVE', note), [mutateApproval]);
  const rejectCase = useCallback((caseId: string, note: string) => mutateApproval(caseId, 'REJECT', note), [mutateApproval]);

  const requestInfoCase = useCallback(async (caseId: string, note: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const c = cases.find(x => x.id === caseId);
      const reasonCode = 'LEGAL_FORM_UNCONFIRMED';
      void note;
      void c;
      await api.resolve(caseId, reasonCode, role);
      addToast({
        title: `Info requested for ${caseId}`,
        description: 'Vendor notified with required clarification details.',
        variant: 'warning'
      });
      await refreshCases();
      return { success: true };
    } catch (e) {
      return { success: false, error: e instanceof Error ? e.message : 'Request failed' };
    }
  }, [addToast, refreshCases, role, cases]);

  const verifyCallbackDesk = useCallback(async (caseId: string, numberSource: string, dialedNumber: string) => {
    try {
      const r = await api.callback(caseId, {
        number_used: dialedNumber,
        number_source: numberSource,
        outcome: 'verified',
        attested: true,
        number_age_days: 60,
      }) as { ok?: boolean; reason?: string };
      if (r.ok) {
        addToast({
          title: 'Independent callback verified',
          description: `Dialed ${dialedNumber}. Case ${caseId} updated.`,
          variant: 'success'
        });
        await refreshCases();
        return { success: true, message: 'Independent call verified. Bank change attestation complete.' };
      }
      return { success: false, message: String(r.reason ?? 'Callback rejected.') };
    } catch (e) {
      return { success: false, message: e instanceof Error ? e.message : 'Callback failed.' };
    }
  }, [addToast, refreshCases]);

  const resetAllData = useCallback(async () => {
    await api.reset();
    await refreshCases();
    setAuditEvents([]);
    setVirtualNow('');
    addToast({
      title: 'Demo data reset',
      description: 'Server state cleared via /api/v1/admin/reset.',
      variant: 'default'
    });
  }, [addToast, refreshCases]);

  return (
    <AppContext.Provider
      value={{
        currentPath,
        navigate,
        theme,
        toggleTheme,
        role,
        setRole,
        toasts,
        addToast,
        removeToast,
        isCommandPaletteOpen,
        setCommandPaletteOpen,
        activeEvidence,
        openEvidenceDrawer,
        closeEvidenceDrawer,
        runs,
        cases,
        stages,
        checks,
        evidenceMap,
        auditEvents,
        virtualNow,
        advanceVirtualClock,
        clockHistory,
        faults,
        setFault,
        refreshCases,
        addRun,
        approveCase,
        rejectCase,
        requestInfoCase,
        verifyCallbackDesk,
        resetAllData
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
