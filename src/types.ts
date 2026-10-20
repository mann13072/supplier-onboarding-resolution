export type Contact = { name: string; email: string };
export type TaskType = 'verify_contact' | 'follow_up' | 'investigate_technical';
export type Evidence = { id: string; type: string; title: string; source: string; occurredAt: string; body: string; fields: Record<string, unknown> };
export type Task = { id: string; type: TaskType; title: string; note: string; dueDate: string; assignee: string; status: string; evidenceIds: string[] };
export type Verification = { id: string; candidate: Contact; scopeKey: string; outcome: string; method: string; note: string; verifier: string; evidenceId: string; recordedAt: string };
export type ChangeRequest = { id: string; candidate: Contact; previousContact: Contact; scopeKey: string; status: string; reviewNote: string | null; result: string | null; approvedEvidenceVersion: number | null };
export type SupplierCase = {
  id: string; rolloutId: string; caseType: string; owner: string;
  supplier: { name: string; number: string; site: string; country: string; commodity: string };
  relationship: { buyerId: string; buyerName: string; plant: string; siteId: string; workflow: string };
  sourceSnapshot: { source: string; importedAt: string; lastEditedAt: string; contact: Contact; readOnly: boolean };
  currentContact: Contact; candidate: Contact | null; events: Evidence[]; tasks: Task[]; verifications: Verification[];
  requests: ChangeRequest[]; registered: boolean; testPassed: boolean; version: number; evidenceVersion: number;
  scopeKey: string; milestone: string; variant: 'accepted' | 'rejected'; demoTime: string;
  assessment: { provider: string; category: string; severity: string; facts: { text: string; evidenceIds: string[] }[]; unknowns: string[]; nextAction: string; taskType: TaskType | null; canPropose: boolean };
  audit: { seq: number; actor: string; action: string; details: string; recorded_at: string }[];
};
export type Rollout = { id: string; name: string; buyer: string; plant: string; target: string; demoTime: string; variant: 'accepted' | 'rejected'; cases: SupplierCase[] };
