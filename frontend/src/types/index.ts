export type StatusType = 'APPROVED' | 'PENDING' | 'REJECTED' | 'UNVERIFIABLE' | 'BLOCKED' | 'SKIPPED' | 'PASS' | 'WARN' | 'FAIL';
export type TierType = 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKED';
export type RoleType = 'Requester' | 'AP Analyst' | 'Controller' | 'Compliance' | 'Auditor' | 'Admin';

export interface Stage {
  id: string; // S0 - S12
  code: string;
  name: string;
  checksCount: number;
  status: 'pending' | 'running' | 'completed' | 'skipped';
  cached?: boolean;
}

export interface CheckItem {
  id: string; // e.g. C-NAME-02
  stageId: string;
  title: string;
  subject: string;
  outcome: 'PASS' | 'WARN' | 'FAIL' | 'UNVERIFIABLE' | 'SKIPPED';
  durationMs: number;
  cached: boolean;
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reasonCode?: string;
  fixedBy?: string;
  resolvedInV2?: boolean;
  introducedAfterFix?: boolean;
  evidenceRef?: string;
}

export interface Claim {
  path: string;
  value: string;
  source: 'FORM' | 'DOC' | 'REGISTRY' | 'BANK' | 'SCREENING' | 'LLM';
  confidence: number;
  quote?: string;
  page?: number;
  docName?: string;
}

export interface FindingEvidence {
  checkId: string;
  title: string;
  outcome: 'PASS' | 'WARN' | 'FAIL' | 'UNVERIFIABLE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  subtitle: string;
  reasonCode: string;
  fixedBy: string;
  durationMs: number;
  cached: boolean;
  deterministic: boolean;
  items: {
    kind: 'claim' | 'rule' | 'adapter' | 'llm' | 'policy';
    ref: string;
    summary: string;
    claimDetails?: {
      path: string;
      rawValue: string;
      source: string;
      page?: number;
      quote: string;
    };
    adapterDetails?: {
      callId: string;
      version: string;
      retrievedAt: string;
      latencyMs: number;
    };
  }[];
  ruleSnippet: string;
  policySlice: string;
  llmRationale?: {
    verdict: string;
    confidence: number;
    orderSwapConsistent: boolean;
    corroborators: string[];
    note: string;
  };
}

export interface RunRecord {
  id: string; // e.g. run-8842
  caseId: string;
  vendorName: string;
  submittedAt: string;
  mode: 'hybrid' | 'rules-only' | 'llm-only';
  status: 'APPROVED' | 'PENDING' | 'REJECTED';
  tier: TierType;
  score: number;
  durationMs: number;
  cached: boolean;
  isDelta?: boolean;
  deltaSummary?: string;
  claimsCount: number;
  cacheHitCount: number;
  totalChecks: number;
  llmCalls: number;
  costUsd: number;
  riskComponents: {
    name: string;
    points: number;
    max: number;
  }[];
}

export interface CaseRecord {
  id: string; // e.g. case-1049
  vendorName: string;
  submittedAt: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED';
  tier: TierType;
  score: number;
  awaitingRole?: RoleType | 'VENDOR';
  waitingSinceHours: number;
  requesterEmail: string;
  country: string;
  spendAmount: number;
  currency: string;
  hasBankChange: boolean;
  reasonCodes: string[];
  counterfactual?: {
    targetStatus: 'APPROVED';
    targetScore: number;
    itemsCount: number;
    caveat: string;
    blockingItems: {
      number: number;
      reasonCode: string;
      title: string;
      whatYouNeedToDo: string;
      severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
      canVendorFix: boolean;
    }[];
  };
  policyHash: string;
  engineVersion: string;
  datasetHash: string;
}

export interface AuditEvent {
  sequence: number;
  timestamp: string;
  actor: string;
  eventType: string;
  summary: string;
  hash: string;
  prevHash: string;
  payload: Record<string, unknown>;
}

export interface VendorMaster {
  id: string;
  name: string;
  taxIdMasked: string;
  country: string;
  tier: TierType;
  status: 'APPROVED' | 'PENDING' | 'REJECTED';
  createdAt: string;
  lastVerifiedAt: string;
  hasBankChange: boolean;
  contactName: string;
  contactEmail: string;
  address: string;
  masterPhone: string;
  owners: { name: string; percentage: number; role: string }[];
  scoreHistory: number[];
  associatedCases: string[];
}

export interface NetworkNode {
  id: string;
  label: string;
  type: 'vendor' | 'bank' | 'phone' | 'domain' | 'address';
  flagged?: boolean;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  flagged?: boolean;
  sharedAttribute?: string;
  vendorPair?: [string, string];
}
