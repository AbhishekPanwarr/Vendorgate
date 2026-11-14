import type {
  AuditEvent,
  CaseRecord,
  CheckItem,
  Claim,
  FindingEvidence,
  RoleType,
  RunRecord,
  Stage,
  VendorMaster,
} from './types';

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return (await r.json()) as T;
}

async function post<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
  const j = (await r.json().catch(() => ({}))) as T & { type?: string };
  if (!r.ok) throw Object.assign(new Error(j.type || `POST ${path} -> ${r.status}`), { body: j });
  return j as T;
}

// ---------------------------------------------------------------------------
// Raw API shapes (subset of backend/app/main.py responses)
// ---------------------------------------------------------------------------

export interface ApiCase {
  case_id: string;
  status: string;
  tier: string;
  score?: number;
  reason_codes?: string[];
  approval_route?: string[];
  requester?: string;
  run_id?: string;
  current_version?: number;
  [k: string]: unknown;
}

export interface ApiRun {
  run_id: string;
  case_id: string;
  mode?: string;
  payload?: Record<string, unknown>;
  decision?: Record<string, unknown>;
  findings?: Record<string, unknown>[];
  claims?: Record<string, unknown>[];
  adjudications?: Record<string, unknown>[];
  check_stats?: { rerun?: string[]; cached?: string[] };
  delta?: Record<string, unknown> | null;
  audit?: Record<string, unknown>[];
  message?: Record<string, unknown>;
  [k: string]: unknown;
}

// ---------------------------------------------------------------------------
// Mappers: real API shapes -> existing view-model types (visuals unchanged)
// ---------------------------------------------------------------------------

const num = (v: unknown, d = 0): number => (typeof v === 'number' && Number.isFinite(v) ? v : d);
const str = (v: unknown, d = ''): string => (typeof v === 'string' ? v : d);

export function mapRun(pack: ApiRun, vendorFallback = ''): RunRecord {
  const dec = (pack.decision ?? {}) as Record<string, unknown>;
  const score = (dec.score ?? {}) as Record<string, unknown>;
  const comps = (score.components ?? {}) as Record<string, { points?: number }>;
  const names = ['SPEND', 'GEO', 'DOCS', 'BANK_ID', 'CATEGORY', 'REGISTRY_MEDIA'];
  const payload = (pack.payload ?? {}) as Record<string, unknown>;
  const company = (payload.company ?? {}) as Record<string, unknown>;
  return {
    id: str(pack.run_id),
    caseId: str(pack.case_id),
    vendorName: str(company.legal_name, vendorFallback),
    submittedAt: '',
    mode: 'hybrid',
    status: (dec.status as RunRecord['status']) ?? 'PENDING',
    tier: (dec.tier as RunRecord['tier']) ?? 'LOW',
    score: num(score.total),
    durationMs: 0,
    cached: false,
    claimsCount: Array.isArray(pack.claims) ? pack.claims.length : 0,
    cacheHitCount: pack.check_stats?.cached?.length ?? 0,
    totalChecks: Array.isArray(pack.findings) ? pack.findings.length : 0,
    llmCalls: 0,
    costUsd: 0,
    riskComponents: names.map((name) => ({ name, points: num(comps[name]?.points), max: 25 })),
  };
}

export interface MappedCase {
  record: import('./types').CaseRecord;
  reasonCodes: string[];
  status: string;
  tier: string;
}

export function mapCaseWithCodes(row: ApiCase, run?: ApiRun): MappedCase {
  return {
    record: mapCase(row, run),
    reasonCodes: Array.isArray(row.reason_codes) ? (row.reason_codes as string[]) : [],
    status: str(row.status, 'PENDING'),
    tier: str(row.tier, 'LOW'),
  };
}

export function mapCase(row: ApiCase, run?: ApiRun): CaseRecord {
  const payload = (run?.payload ?? {}) as Record<string, unknown>;
  const company = (payload.company ?? {}) as Record<string, unknown>;
  const requester = (payload.requester ?? {}) as Record<string, unknown>;
  const spend = (requester.expected_annual_spend ?? {}) as Record<string, unknown>;
  const dec = (run?.decision ?? {}) as Record<string, unknown>;
  const awaiting = (Array.isArray(dec.awaiting) ? dec.awaiting : []) as string[];
  const route = (Array.isArray(dec.approval_route) ? dec.approval_route : []) as string[];
  const roleLabel: Record<string, string> = { AP_ANALYST: 'AP Analyst', CONTROLLER: 'Controller', COMPLIANCE: 'Compliance' };
  const awaitingRole = awaiting.includes('VENDOR')
    ? 'VENDOR'
    : awaiting.includes('INTERNAL')
      ? (roleLabel[route[0]] ?? route[0] ?? 'Controller')
      : undefined;
  const cfs = (dec.counterfactuals ?? []) as Record<string, unknown>[];
  const cf = cfs[0];
  return {
    id: str(row.case_id),
    vendorName: str(company.legal_name),
    submittedAt: '',
    status: (row.status as CaseRecord['status']) ?? 'PENDING',
    tier: (row.tier as CaseRecord['tier']) ?? 'LOW',
    score: num(row.score),
    awaitingRole: awaitingRole as CaseRecord['awaitingRole'],
    waitingSinceHours: 0,
    requesterEmail: str(requester.email),
    country: str(company.country),
    spendAmount: num(spend.amount),
    currency: str(spend.currency, 'USD'),
    hasBankChange: str((payload as Record<string, unknown>).submission_type) === 'CHANGE_REQUEST',
    reasonCodes: Array.isArray(dec.reason_codes) ? (dec.reason_codes as string[]) : [],
    counterfactual: cf
      ? {
          targetStatus: 'APPROVED',
          targetScore: num(cf.score),
          itemsCount: ((cf.fix_set ?? []) as unknown[]).length,
          caveat: str(cf.note, 'assumes no new issues are found'),
          blockingItems: (Array.isArray(dec.required_actions) ? dec.required_actions : []).map(
            (a: unknown, i: number) => {
              const ra = a as Record<string, unknown>;
              return {
                number: i + 1,
                reasonCode: str(ra.code),
                title: str(ra.title, str(ra.code)),
                whatYouNeedToDo: str(ra.detail, ((ra.field_paths ?? []) as unknown[]).join(', ')),
                severity: 'MEDIUM' as const,
                canVendorFix: false,
              };
            },
          ),
        }
      : undefined,
    policyHash: '',
    engineVersion: '',
    datasetHash: '',
  };
}

export function mapCheck(f: Record<string, unknown>, stageId: string): CheckItem {
  const outcome = str(f.outcome, 'PASS') as CheckItem['outcome'];
  const sev = num(f.severity, 0);
  return {
    id: str(f.check_id),
    stageId,
    title: str(f.title),
    subject: str(f.subject),
    outcome: outcome === 'FAIL' || outcome === 'WARN' || outcome === 'UNVERIFIABLE' ? outcome : 'PASS',
    durationMs: num(f.duration_ms),
    cached: Boolean(f.cached),
    severity: sev >= 3 ? 'CRITICAL' : sev === 2 ? 'HIGH' : sev === 1 ? 'MEDIUM' : 'LOW',
    reasonCode: f.reason_code == null ? undefined : str(f.reason_code),
    fixedBy: str(f.fixed_by),
  };
}

export function mapEvidence(f: Record<string, unknown>): FindingEvidence {
  const sev = num(f.severity, 0);
  const items = (Array.isArray(f.evidence) ? f.evidence : []).map((e) => {
    const ev = e as Record<string, unknown>;
    return {
      kind: (['claim', 'rule', 'adapter', 'llm', 'policy'] as const).includes(ev.kind as never)
        ? (ev.kind as 'claim' | 'rule' | 'adapter' | 'llm' | 'policy')
        : ('rule' as const),
      ref: str(ev.ref),
      summary: str(ev.summary),
    };
  });
  return {
    checkId: str(f.check_id),
    title: str(f.title),
    outcome: (['PASS', 'WARN', 'FAIL', 'UNVERIFIABLE'] as const).includes(f.outcome as never)
      ? (f.outcome as FindingEvidence['outcome'])
      : 'PASS',
    severity: sev >= 3 ? 'CRITICAL' : sev === 2 ? 'HIGH' : sev === 1 ? 'MEDIUM' : 'LOW',
    subtitle: `${str(f.check_id)} · ${str(f.stage)}`,
    reasonCode: str(f.reason_code),
    fixedBy: str(f.fixed_by),
    durationMs: num(f.duration_ms),
    cached: Boolean(f.cached),
    deterministic: f.deterministic !== false,
    items,
    ruleSnippet: str(f.detail).slice(0, 280),
    policySlice: (Array.isArray(f.reads) ? (f.reads as unknown[]).join(', ') : '').slice(0, 280),
  };
}

export function mapClaim(c: Record<string, unknown>): Claim {
  return {
    path: str(c.path),
    value: str(c.value ?? c.raw),
    source: (['FORM', 'DOC', 'REGISTRY', 'BANK', 'SCREENING'] as const).includes(c.source as never)
      ? (c.source as Claim['source'])
      : 'FORM',
    confidence: num(c.confidence, 1),
    quote: typeof c.quote === 'string' ? c.quote : undefined,
    page: typeof c.page === 'number' ? c.page : undefined,
    docName: typeof c.doc_id === 'string' ? c.doc_id : undefined,
  };
}

export function mapAuditEvent(e: Record<string, unknown>, i: number): AuditEvent {
  return {
    sequence: num(e.seq ?? e.sequence, i),
    timestamp: str(e.ts ?? e.timestamp),
    actor: str(e.actor, 'system'),
    eventType: str(e.type ?? e.eventType),
    summary: str(e.summary ?? e.type),
    hash: str(e.hash),
    prevHash: str(e.prev_hash ?? e.prevHash),
    payload: (e.payload ?? {}) as Record<string, unknown>,
  };
}

export function mapStages(): Stage[] {
  const defs: [string, string, number][] = [
    ['S0', 'Intake', 0], ['S1', 'Documents', 0], ['S2', 'Completeness', 0],
    ['S3', 'Format', 0], ['S4', 'Verification', 0], ['S5', 'Consistency', 0],
    ['S6', 'Duplicates', 0], ['S7', 'Screening', 0], ['S8', 'Adjudication', 0],
    ['S9', 'Scoring', 0], ['S10', 'Decision', 0], ['S11', 'Comms', 0], ['S12', 'Persist', 0],
  ];
  return defs.map(([code, name], i) => ({
    id: `s${i}`, code, name, checksCount: 0, status: 'completed' as const,
  }));
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export const api = {
  getCases: () => get<ApiCase[]>(`/api/v1/cases`),
  getCase: (id: string) => get<ApiCase & { run?: ApiRun }>(`/api/v1/cases/${id}`),
  getRun: (id: string) => get<ApiRun>(`/api/v1/runs/${id}`),
  getMessages: (caseId: string) => get<Record<string, unknown>>(`/api/v1/cases/${caseId}/messages`),
  getVendors: () => get<Record<string, unknown>[]>(`/api/v1/vendors`),
  getApprovals: (role: string) => get<ApiCase[]>(`/api/v1/approvals?role=${encodeURIComponent(role)}`),
  getPolicy: () => get<{ assumptions: { id: string; text: string }[]; policy_hash: string }>(`/api/v1/policy`),
  getEvalLatest: () => get<Record<string, unknown>>(`/api/v1/eval/latest`),
  getFoolItOperators: () =>
    get<{ id: string; name: string; description: string; expected: Record<string, unknown> }[]>(
      `/api/v1/foolit/operators`,
    ),
  getAudit: (caseId: string) => get<Record<string, unknown>[]>(`/api/v1/cases/${caseId}/audit`),
  verifyAudit: (caseId: string) => get<{ ok: boolean; length?: number; broken_at?: number }>(
    `/api/v1/cases/${caseId}/audit/verify`,
  ),
  getCaseEvents: (caseId: string) => get<Record<string, unknown>[]>(`/api/v1/cases/${caseId}/events`),

  submit: async (payload: Record<string, unknown>, files: { docId: string; name: string; data: Blob }[]) => {
    const fd = new FormData();
    fd.append('payload', JSON.stringify(payload));
    for (const f of files) fd.append(`file:${f.docId}`, f.data, f.name);
    const r = await fetch('/api/v1/submissions', {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: fd,
    });
    if (!r.ok) throw new Error(`submit -> ${r.status}`);
    return (await r.json()) as { case_id: string; run_id: string };
  },

  resubmit: async (caseId: string, version: number, payload: Record<string, unknown>) => {
    const fd = new FormData();
    fd.append('payload', JSON.stringify(payload));
    const r = await fetch(`/api/v1/cases/${caseId}/resubmit`, {
      method: 'POST',
      headers: { 'If-Match': String(version), 'Idempotency-Key': crypto.randomUUID() },
      body: fd,
    });
    const j = (await r.json().catch(() => ({}))) as Record<string, unknown>;
    if (!r.ok) throw Object.assign(new Error(String(j.type ?? `resubmit -> ${r.status}`)), { body: j });
    return j as { case_id: string; run_id: string; new_version: number };
  },

  approve: (caseId: string, action: 'APPROVE' | 'REJECT', note: string, actor: string, role: string) =>
    post<Record<string, unknown>>(
      `/api/v1/cases/${caseId}/approvals`,
      { action, note },
      { 'X-Actor': actor, 'X-Role': role },
    ),

  resolve: (caseId: string, reasonCode: string, role: string) =>
    post<Record<string, unknown>>(
      `/api/v1/cases/${caseId}/resolutions`,
      { reason_code: reasonCode, action: 'NOTE' },
      { 'X-Role': role },
    ),

  callback: (caseId: string, body: Record<string, unknown>) =>
    post<Record<string, unknown>>(`/api/v1/cases/${caseId}/callback`, body),

  appeal: (caseId: string, body: Record<string, unknown>, headers: Record<string, string> = {}) =>
    post<Record<string, unknown>>(`/api/v1/cases/${caseId}/appeal`, body, headers),

  foolitRun: (vendor_id: string, ops: string[]) =>
    post<{ expected: Record<string, unknown>; actual: Record<string, unknown>; match: boolean }>(
      `/api/v1/foolit/run`,
      { vendor_id, ops },
    ),

  reset: () => post<{ ok: boolean; duration_ms: number }>(`/api/v1/admin/reset`, {}),
  clockAdvance: (days: number) =>
    post<{ now: string; jobs_fired: unknown }>(`/api/v1/admin/clock/advance`, { days }),
};

export type { RoleType };
