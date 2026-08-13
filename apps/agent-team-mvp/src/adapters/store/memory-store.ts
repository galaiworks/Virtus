/**
 * インメモリ Store。テスト・評価セット・デモで使う。
 *
 * `transaction` はテーブル全体のスナップショットを取り、
 * コールバックが投げた場合に丸ごと戻す。承認・状態・実行を
 * 同一の一貫性単位で扱う要件(非機能要件「整合性」)を満たす。
 */

import type { Store, StoreSession } from '../../ports/store.js';
import type {
  AgentRun,
  ApprovalDecisionRecord,
  ApprovalRequestRecord,
  ApprovalRequestStatus,
  ArtifactRecord,
  AuditEvent,
  CaseRecord,
  ExecutionJobRecord,
  RetryCounterRecord,
  SourceDocument,
} from '../../domain/types.js';
import type { ExceptionCategory } from '../../domain/schemas.js';

interface Tables {
  cases: CaseRecord[];
  sources: SourceDocument[];
  agentRuns: AgentRun[];
  artifacts: ArtifactRecord[];
  approvalRequests: ApprovalRequestRecord[];
  approvalDecisions: ApprovalDecisionRecord[];
  executionJobs: ExecutionJobRecord[];
  auditEvents: AuditEvent[];
  retryCounters: RetryCounterRecord[];
}

function emptyTables(): Tables {
  return {
    cases: [],
    sources: [],
    agentRuns: [],
    artifacts: [],
    approvalRequests: [],
    approvalDecisions: [],
    executionJobs: [],
    auditEvents: [],
    retryCounters: [],
  };
}

const clone = <T>(value: T): T => structuredClone(value);

export class MemoryStore implements Store {
  private tables: Tables = emptyTables();
  private inTransaction = false;

  async transaction<T>(fn: (tx: StoreSession) => Promise<T>): Promise<T> {
    if (this.inTransaction) {
      // 入れ子はセーブポイントを作らず、外側の一貫性単位に委ねる。
      return fn(this);
    }
    const snapshot = clone(this.tables);
    this.inTransaction = true;
    try {
      return await fn(this);
    } catch (error) {
      this.tables = snapshot;
      throw error;
    } finally {
      this.inTransaction = false;
    }
  }

  async close(): Promise<void> {
    this.tables = emptyTables();
  }

  /* ----- cases ----- */

  async insertCase(record: CaseRecord): Promise<void> {
    if (this.tables.cases.some((c) => c.case_id === record.case_id)) {
      throw new Error(`case_id が重複しています: ${record.case_id}`);
    }
    this.tables.cases.push(clone(record));
  }

  async getCase(caseId: string): Promise<CaseRecord | null> {
    const found = this.tables.cases.find((c) => c.case_id === caseId);
    return found ? clone(found) : null;
  }

  async updateCase(record: CaseRecord): Promise<void> {
    const index = this.tables.cases.findIndex((c) => c.case_id === record.case_id);
    if (index < 0) throw new Error(`案件が見つかりません: ${record.case_id}`);
    this.tables.cases[index] = clone(record);
  }

  async listCases(): Promise<CaseRecord[]> {
    return clone(this.tables.cases);
  }

  /* ----- sources ----- */

  async insertSource(record: SourceDocument): Promise<void> {
    this.tables.sources.push(clone(record));
  }

  async listSources(caseId: string): Promise<SourceDocument[]> {
    return clone(this.tables.sources.filter((s) => s.case_id === caseId));
  }

  /* ----- agent runs ----- */

  async insertAgentRun(record: AgentRun): Promise<void> {
    this.tables.agentRuns.push(clone(record));
  }

  async listAgentRuns(caseId: string): Promise<AgentRun[]> {
    return clone(this.tables.agentRuns.filter((r) => r.case_id === caseId));
  }

  /* ----- artifacts ----- */

  async insertArtifact(record: ArtifactRecord): Promise<void> {
    this.tables.artifacts.push(clone(record));
  }

  async listArtifacts(caseId: string): Promise<ArtifactRecord[]> {
    return clone(this.tables.artifacts.filter((a) => a.case_id === caseId));
  }

  async latestArtifact(
    caseId: string,
    kind: ArtifactRecord['kind'],
  ): Promise<ArtifactRecord | null> {
    const matching = this.tables.artifacts
      .filter((a) => a.case_id === caseId && a.kind === kind)
      .sort((a, b) => a.version - b.version);
    const last = matching.at(-1);
    return last ? clone(last) : null;
  }

  /* ----- approvals ----- */

  async insertApprovalRequest(record: ApprovalRequestRecord): Promise<void> {
    this.tables.approvalRequests.push(clone(record));
  }

  async getApprovalRequest(requestId: string): Promise<ApprovalRequestRecord | null> {
    const found = this.tables.approvalRequests.find((r) => r.request_id === requestId);
    return found ? clone(found) : null;
  }

  async updateApprovalRequest(record: ApprovalRequestRecord): Promise<void> {
    const index = this.tables.approvalRequests.findIndex(
      (r) => r.request_id === record.request_id,
    );
    if (index < 0) throw new Error(`承認要求が見つかりません: ${record.request_id}`);
    this.tables.approvalRequests[index] = clone(record);
  }

  async listApprovalRequests(caseId: string): Promise<ApprovalRequestRecord[]> {
    return clone(this.tables.approvalRequests.filter((r) => r.case_id === caseId));
  }

  async claimApprovalRequest(args: {
    requestId: string;
    expectedStatus: ApprovalRequestStatus;
    cardVersion: number;
    nonce: string;
  }): Promise<ApprovalRequestRecord | null> {
    const index = this.tables.approvalRequests.findIndex(
      (r) => r.request_id === args.requestId,
    );
    if (index < 0) return null;
    const record = this.tables.approvalRequests[index] as ApprovalRequestRecord;
    if (record.status !== args.expectedStatus) return null;
    if (record.nonce_consumed) return null;
    if (record.packet.card_version !== args.cardVersion) return null;
    if (record.packet.nonce !== args.nonce) return null;

    const claimed: ApprovalRequestRecord = { ...clone(record), nonce_consumed: true };
    this.tables.approvalRequests[index] = claimed;
    return clone(claimed);
  }

  async insertApprovalDecision(record: ApprovalDecisionRecord): Promise<void> {
    this.tables.approvalDecisions.push(clone(record));
  }

  async listApprovalDecisions(caseId: string): Promise<ApprovalDecisionRecord[]> {
    return clone(this.tables.approvalDecisions.filter((d) => d.case_id === caseId));
  }

  /* ----- execution ----- */

  async findExecutionByIdempotencyKey(key: string): Promise<ExecutionJobRecord | null> {
    const found = this.tables.executionJobs.find(
      (j) => j.idempotency_key === key && j.status !== 'failed',
    );
    return found ? clone(found) : null;
  }

  async insertExecutionJob(record: ExecutionJobRecord): Promise<void> {
    this.tables.executionJobs.push(clone(record));
  }

  async listExecutionJobs(caseId: string): Promise<ExecutionJobRecord[]> {
    return clone(this.tables.executionJobs.filter((j) => j.case_id === caseId));
  }

  /* ----- audit ----- */

  async insertAuditEvent(record: AuditEvent): Promise<void> {
    this.tables.auditEvents.push(clone(record));
  }

  async listAuditEvents(caseId: string): Promise<AuditEvent[]> {
    return clone(this.tables.auditEvents.filter((e) => e.case_id === caseId));
  }

  /* ----- retry counters ----- */

  async getRetryCounter(
    caseId: string,
    category: ExceptionCategory,
    rootCause: string,
  ): Promise<RetryCounterRecord | null> {
    const found = this.tables.retryCounters.find(
      (r) => r.case_id === caseId && r.category === category && r.root_cause === rootCause,
    );
    return found ? clone(found) : null;
  }

  async upsertRetryCounter(record: RetryCounterRecord): Promise<void> {
    const index = this.tables.retryCounters.findIndex(
      (r) =>
        r.case_id === record.case_id &&
        r.category === record.category &&
        r.root_cause === record.root_cause,
    );
    if (index < 0) this.tables.retryCounters.push(clone(record));
    else this.tables.retryCounters[index] = clone(record);
  }

  async listRetryCounters(caseId: string): Promise<RetryCounterRecord[]> {
    return clone(this.tables.retryCounters.filter((r) => r.case_id === caseId));
  }
}
