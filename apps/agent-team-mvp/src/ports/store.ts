/**
 * 永続化のポート。
 *
 * 非機能要件「整合性」より、承認・案件状態・実行はひとつの一貫性単位で更新する。
 * `transaction` の中で行った更新は、コールバックが例外を投げた場合すべて破棄される。
 */

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
} from '../domain/types.js';
import type { ExceptionCategory } from '../domain/schemas.js';

export interface StoreSession {
  /* cases */
  insertCase(record: CaseRecord): Promise<void>;
  getCase(caseId: string): Promise<CaseRecord | null>;
  updateCase(record: CaseRecord): Promise<void>;
  listCases(): Promise<CaseRecord[]>;

  /* source_documents */
  insertSource(record: SourceDocument): Promise<void>;
  listSources(caseId: string): Promise<SourceDocument[]>;

  /* agent_runs */
  insertAgentRun(record: AgentRun): Promise<void>;
  listAgentRuns(caseId: string): Promise<AgentRun[]>;

  /* artifacts */
  insertArtifact(record: ArtifactRecord): Promise<void>;
  listArtifacts(caseId: string): Promise<ArtifactRecord[]>;
  /** 最新版の成果物を取得する。 */
  latestArtifact(caseId: string, kind: ArtifactRecord['kind']): Promise<ArtifactRecord | null>;

  /* approval_requests / approval_decisions */
  insertApprovalRequest(record: ApprovalRequestRecord): Promise<void>;
  getApprovalRequest(requestId: string): Promise<ApprovalRequestRecord | null>;
  updateApprovalRequest(record: ApprovalRequestRecord): Promise<void>;
  listApprovalRequests(caseId: string): Promise<ApprovalRequestRecord[]>;
  /**
   * 状態と nonce を条件に承認要求を確保する。
   * 条件を満たさない場合は null を返し、呼び出し側は操作を拒否する(FR-033)。
   */
  claimApprovalRequest(args: {
    requestId: string;
    expectedStatus: ApprovalRequestStatus;
    cardVersion: number;
    nonce: string;
  }): Promise<ApprovalRequestRecord | null>;
  insertApprovalDecision(record: ApprovalDecisionRecord): Promise<void>;
  listApprovalDecisions(caseId: string): Promise<ApprovalDecisionRecord[]>;

  /* execution_jobs */
  /**
   * 冪等性キーで既存ジョブを引く(FR-041)。
   * 既に成功しているジョブがあれば二重実行しない。
   */
  findExecutionByIdempotencyKey(key: string): Promise<ExecutionJobRecord | null>;
  insertExecutionJob(record: ExecutionJobRecord): Promise<void>;
  listExecutionJobs(caseId: string): Promise<ExecutionJobRecord[]>;

  /* audit_events */
  insertAuditEvent(record: AuditEvent): Promise<void>;
  listAuditEvents(caseId: string): Promise<AuditEvent[]>;

  /* retry counters (FR-022) */
  getRetryCounter(
    caseId: string,
    category: ExceptionCategory,
    rootCause: string,
  ): Promise<RetryCounterRecord | null>;
  upsertRetryCounter(record: RetryCounterRecord): Promise<void>;
  listRetryCounters(caseId: string): Promise<RetryCounterRecord[]>;
}

export interface Store extends StoreSession {
  /** 一貫性単位。コールバックが投げた場合はすべて破棄する。 */
  transaction<T>(fn: (tx: StoreSession) => Promise<T>): Promise<T>;
  close(): Promise<void>;
}
