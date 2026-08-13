/**
 * PostgreSQL Store(要件定義 §8「データ」)。
 *
 * `transaction` は 1 本のコネクションを BEGIN / COMMIT / ROLLBACK で束ねる。
 * 承認の確保(`claimApprovalRequest`)は単一 UPDATE 文の条件で行い、
 * 二重操作・古いカード・nonce 再利用をデータベース側で弾く(FR-033)。
 */

import { Pool } from 'pg';
import type { PoolClient, QueryResult, QueryResultRow } from 'pg';
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

interface Queryable {
  query<R extends QueryResultRow = QueryResultRow>(
    text: string,
    values?: unknown[],
  ): Promise<QueryResult<R>>;
}

const iso = (value: Date | string | null): string | null =>
  value === null ? null : value instanceof Date ? value.toISOString() : value;

const isoRequired = (value: Date | string): string =>
  value instanceof Date ? value.toISOString() : value;

class PgSession implements StoreSession {
  constructor(protected readonly db: Queryable) {}

  /* ----- cases ----- */

  async insertCase(record: CaseRecord): Promise<void> {
    await this.db.query(
      `INSERT INTO cases (case_id, objective, due_date, desired_artifacts, target_workflow,
         business_owner, approver, permitted_operations, permitted_personal_data, actor_roles,
         state, stage, risk, created_at, updated_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)`,
      [
        record.case_id,
        record.objective,
        record.due_date,
        JSON.stringify(record.desired_artifacts),
        record.target_workflow,
        record.business_owner,
        record.approver,
        JSON.stringify(record.permitted_operations),
        JSON.stringify(record.permitted_personal_data),
        JSON.stringify(record.actor_roles),
        record.state,
        record.stage,
        record.risk,
        record.created_at,
        record.updated_at,
      ],
    );
  }

  async getCase(caseId: string): Promise<CaseRecord | null> {
    const { rows } = await this.db.query(`SELECT * FROM cases WHERE case_id = $1`, [caseId]);
    return rows[0] ? this.toCase(rows[0]) : null;
  }

  async updateCase(record: CaseRecord): Promise<void> {
    const { rowCount } = await this.db.query(
      `UPDATE cases SET objective=$2, due_date=$3, desired_artifacts=$4, target_workflow=$5,
         business_owner=$6, approver=$7, permitted_operations=$8, permitted_personal_data=$9,
         actor_roles=$10, state=$11, stage=$12, risk=$13, updated_at=$14
       WHERE case_id=$1`,
      [
        record.case_id,
        record.objective,
        record.due_date,
        JSON.stringify(record.desired_artifacts),
        record.target_workflow,
        record.business_owner,
        record.approver,
        JSON.stringify(record.permitted_operations),
        JSON.stringify(record.permitted_personal_data),
        JSON.stringify(record.actor_roles),
        record.state,
        record.stage,
        record.risk,
        record.updated_at,
      ],
    );
    if (rowCount === 0) throw new Error(`案件が見つかりません: ${record.case_id}`);
  }

  async listCases(): Promise<CaseRecord[]> {
    const { rows } = await this.db.query(`SELECT * FROM cases ORDER BY created_at DESC`);
    return rows.map((r) => this.toCase(r));
  }

  private toCase(row: QueryResultRow): CaseRecord {
    return {
      case_id: row.case_id,
      objective: row.objective,
      due_date: row.due_date,
      desired_artifacts: row.desired_artifacts ?? [],
      target_workflow: row.target_workflow,
      business_owner: row.business_owner,
      approver: row.approver,
      permitted_operations: row.permitted_operations ?? [],
      permitted_personal_data: row.permitted_personal_data ?? [],
      actor_roles: row.actor_roles ?? [],
      state: row.state,
      stage: row.stage,
      risk: row.risk,
      created_at: isoRequired(row.created_at),
      updated_at: isoRequired(row.updated_at),
    };
  }

  /* ----- sources ----- */

  async insertSource(record: SourceDocument): Promise<void> {
    await this.db.query(
      `INSERT INTO source_documents (source_id, case_id, title, content, classification,
         updated_at, allowed_roles, retention_policy, retention_expires_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
      [
        record.source_id,
        record.case_id,
        record.title,
        record.content,
        record.classification,
        record.updated_at,
        JSON.stringify(record.allowed_roles),
        record.retention_policy,
        record.retention_expires_at,
      ],
    );
  }

  async listSources(caseId: string): Promise<SourceDocument[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM source_documents WHERE case_id = $1 ORDER BY source_id`,
      [caseId],
    );
    return rows.map((row) => ({
      source_id: row.source_id,
      case_id: row.case_id,
      title: row.title,
      content: row.content,
      classification: row.classification,
      updated_at: isoRequired(row.updated_at),
      allowed_roles: row.allowed_roles ?? [],
      retention_policy: row.retention_policy,
      retention_expires_at: iso(row.retention_expires_at),
    }));
  }

  /* ----- agent runs ----- */

  async insertAgentRun(record: AgentRun): Promise<void> {
    await this.db.query(
      `INSERT INTO agent_runs (run_id, case_id, role, input_hash, output_schema_version,
         state, error, started_at, finished_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
      [
        record.run_id,
        record.case_id,
        record.role,
        record.input_hash,
        record.output_schema_version,
        record.state,
        record.error,
        record.started_at,
        record.finished_at,
      ],
    );
  }

  async listAgentRuns(caseId: string): Promise<AgentRun[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM agent_runs WHERE case_id = $1 ORDER BY started_at`,
      [caseId],
    );
    return rows.map((row) => ({
      run_id: row.run_id,
      case_id: row.case_id,
      role: row.role,
      input_hash: row.input_hash,
      output_schema_version: row.output_schema_version,
      state: row.state,
      error: row.error,
      started_at: isoRequired(row.started_at),
      finished_at: isoRequired(row.finished_at),
    }));
  }

  /* ----- artifacts ----- */

  async insertArtifact(record: ArtifactRecord): Promise<void> {
    await this.db.query(
      `INSERT INTO artifacts (artifact_id, case_id, kind, version, payload, created_at)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [
        record.artifact_id,
        record.case_id,
        record.kind,
        record.version,
        JSON.stringify(record.payload),
        record.created_at,
      ],
    );

    // evidence_bundle は claim 単位でも追跡できるよう展開する(FR-011 / FR-042)。
    if (record.kind === 'evidence_bundle' && 'claims' in record.payload) {
      for (const claim of record.payload.claims) {
        await this.db.query(
          `INSERT INTO claims (claim_id, case_id, artifact_id, statement, source_id,
             locator_start, locator_end, locator_quote, source_updated_at, confidence, kind, subject_key)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
           ON CONFLICT (claim_id) DO NOTHING`,
          [
            claim.claim_id,
            record.case_id,
            record.artifact_id,
            claim.statement,
            claim.source_id,
            claim.locator.start,
            claim.locator.end,
            claim.locator.quote,
            claim.source_updated_at,
            claim.confidence,
            claim.kind,
            claim.subject_key,
          ],
        );
      }
    }
  }

  async listArtifacts(caseId: string): Promise<ArtifactRecord[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM artifacts WHERE case_id = $1 ORDER BY created_at, version`,
      [caseId],
    );
    return rows.map((row) => this.toArtifact(row));
  }

  async latestArtifact(
    caseId: string,
    kind: ArtifactRecord['kind'],
  ): Promise<ArtifactRecord | null> {
    const { rows } = await this.db.query(
      `SELECT * FROM artifacts WHERE case_id = $1 AND kind = $2 ORDER BY version DESC LIMIT 1`,
      [caseId, kind],
    );
    return rows[0] ? this.toArtifact(rows[0]) : null;
  }

  private toArtifact(row: QueryResultRow): ArtifactRecord {
    return {
      artifact_id: row.artifact_id,
      case_id: row.case_id,
      kind: row.kind,
      version: row.version,
      payload: row.payload,
      created_at: isoRequired(row.created_at),
    };
  }

  /* ----- approvals ----- */

  async insertApprovalRequest(record: ApprovalRequestRecord): Promise<void> {
    await this.db.query(
      `INSERT INTO approval_requests (request_id, case_id, packet, status, chat_message_id,
         nonce_consumed, created_at, updated_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
      [
        record.request_id,
        record.case_id,
        JSON.stringify(record.packet),
        record.status,
        record.chat_message_id,
        record.nonce_consumed,
        record.created_at,
        record.updated_at,
      ],
    );
  }

  async getApprovalRequest(requestId: string): Promise<ApprovalRequestRecord | null> {
    const { rows } = await this.db.query(
      `SELECT * FROM approval_requests WHERE request_id = $1`,
      [requestId],
    );
    return rows[0] ? this.toApprovalRequest(rows[0]) : null;
  }

  async updateApprovalRequest(record: ApprovalRequestRecord): Promise<void> {
    const { rowCount } = await this.db.query(
      `UPDATE approval_requests SET packet=$2, status=$3, chat_message_id=$4,
         nonce_consumed=$5, updated_at=$6 WHERE request_id=$1`,
      [
        record.request_id,
        JSON.stringify(record.packet),
        record.status,
        record.chat_message_id,
        record.nonce_consumed,
        record.updated_at,
      ],
    );
    if (rowCount === 0) throw new Error(`承認要求が見つかりません: ${record.request_id}`);
  }

  async listApprovalRequests(caseId: string): Promise<ApprovalRequestRecord[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM approval_requests WHERE case_id = $1 ORDER BY created_at`,
      [caseId],
    );
    return rows.map((row) => this.toApprovalRequest(row));
  }

  /**
   * 状態・カード版数・nonce をすべて満たす場合だけ nonce を消費して確保する。
   * 条件を 1 つでも外した操作は null になり、呼び出し側が拒否する。
   */
  async claimApprovalRequest(args: {
    requestId: string;
    expectedStatus: ApprovalRequestStatus;
    cardVersion: number;
    nonce: string;
  }): Promise<ApprovalRequestRecord | null> {
    const { rows } = await this.db.query(
      `UPDATE approval_requests
         SET nonce_consumed = TRUE
       WHERE request_id = $1
         AND status = $2
         AND nonce_consumed = FALSE
         AND (packet->>'card_version')::int = $3
         AND packet->>'nonce' = $4
       RETURNING *`,
      [args.requestId, args.expectedStatus, args.cardVersion, args.nonce],
    );
    return rows[0] ? this.toApprovalRequest(rows[0]) : null;
  }

  private toApprovalRequest(row: QueryResultRow): ApprovalRequestRecord {
    return {
      request_id: row.request_id,
      case_id: row.case_id,
      packet: row.packet,
      status: row.status,
      chat_message_id: row.chat_message_id,
      nonce_consumed: row.nonce_consumed,
      created_at: isoRequired(row.created_at),
      updated_at: isoRequired(row.updated_at),
    };
  }

  async insertApprovalDecision(record: ApprovalDecisionRecord): Promise<void> {
    await this.db.query(
      `INSERT INTO approval_decisions (decision_id, request_id, case_id, decision, reason,
         conditions, decided_by, decided_by_role, decided_at, granted_scope)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
      [
        record.decision_id,
        record.request_id,
        record.case_id,
        record.decision,
        record.reason,
        JSON.stringify(record.conditions),
        record.decided_by,
        record.decided_by_role,
        record.decided_at,
        JSON.stringify(record.granted_scope),
      ],
    );
  }

  async listApprovalDecisions(caseId: string): Promise<ApprovalDecisionRecord[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM approval_decisions WHERE case_id = $1 ORDER BY decided_at`,
      [caseId],
    );
    return rows.map((row) => ({
      decision_id: row.decision_id,
      request_id: row.request_id,
      case_id: row.case_id,
      decision: row.decision,
      reason: row.reason,
      conditions: row.conditions ?? [],
      decided_by: row.decided_by,
      decided_by_role: row.decided_by_role,
      decided_at: isoRequired(row.decided_at),
      granted_scope: row.granted_scope,
    }));
  }

  /* ----- execution ----- */

  async findExecutionByIdempotencyKey(key: string): Promise<ExecutionJobRecord | null> {
    const { rows } = await this.db.query(
      `SELECT * FROM execution_jobs WHERE idempotency_key = $1 AND status <> 'failed' LIMIT 1`,
      [key],
    );
    return rows[0] ? this.toExecutionJob(rows[0]) : null;
  }

  async insertExecutionJob(record: ExecutionJobRecord): Promise<void> {
    await this.db.query(
      `INSERT INTO execution_jobs (execution_id, case_id, operation, target, idempotency_key,
         status, result, rollback_ref, approval_request_id, attempt, error, executed_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)`,
      [
        record.execution_id,
        record.case_id,
        record.operation,
        record.target,
        record.idempotency_key,
        record.status,
        record.result,
        record.rollback_ref,
        record.approval_request_id,
        record.attempt,
        record.error,
        record.executed_at,
      ],
    );
  }

  async listExecutionJobs(caseId: string): Promise<ExecutionJobRecord[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM execution_jobs WHERE case_id = $1 ORDER BY executed_at`,
      [caseId],
    );
    return rows.map((row) => this.toExecutionJob(row));
  }

  private toExecutionJob(row: QueryResultRow): ExecutionJobRecord {
    return {
      execution_id: row.execution_id,
      case_id: row.case_id,
      operation: row.operation,
      target: row.target,
      idempotency_key: row.idempotency_key,
      status: row.status,
      result: row.result,
      rollback_ref: row.rollback_ref,
      approval_request_id: row.approval_request_id,
      attempt: row.attempt,
      error: row.error,
      executed_at: isoRequired(row.executed_at),
    };
  }

  /* ----- audit ----- */

  async insertAuditEvent(record: AuditEvent): Promise<void> {
    await this.db.query(
      `INSERT INTO audit_events (event_id, case_id, event_type, actor, actor_role, occurred_at,
         input_refs, output_refs, decision, approval_request_id, execution_id, detail)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)`,
      [
        record.event_id,
        record.case_id,
        record.event_type,
        record.actor,
        record.actor_role,
        record.occurred_at,
        JSON.stringify(record.input_refs),
        JSON.stringify(record.output_refs),
        record.decision,
        record.approval_request_id,
        record.execution_id,
        JSON.stringify(record.detail),
      ],
    );
  }

  async listAuditEvents(caseId: string): Promise<AuditEvent[]> {
    const { rows } = await this.db.query(
      `SELECT * FROM audit_events WHERE case_id = $1 ORDER BY occurred_at, event_id`,
      [caseId],
    );
    return rows.map((row) => ({
      event_id: row.event_id,
      case_id: row.case_id,
      event_type: row.event_type,
      actor: row.actor,
      actor_role: row.actor_role,
      occurred_at: isoRequired(row.occurred_at),
      input_refs: row.input_refs ?? [],
      output_refs: row.output_refs ?? [],
      decision: row.decision,
      approval_request_id: row.approval_request_id,
      execution_id: row.execution_id,
      detail: row.detail ?? {},
    }));
  }

  /* ----- retry counters ----- */

  async getRetryCounter(
    caseId: string,
    category: ExceptionCategory,
    rootCause: string,
  ): Promise<RetryCounterRecord | null> {
    const { rows } = await this.db.query(
      `SELECT * FROM retry_counters WHERE case_id=$1 AND category=$2 AND root_cause=$3`,
      [caseId, category, rootCause],
    );
    const row = rows[0];
    return row
      ? {
          case_id: row.case_id,
          category: row.category,
          root_cause: row.root_cause,
          auto_revisions: row.auto_revisions,
        }
      : null;
  }

  async upsertRetryCounter(record: RetryCounterRecord): Promise<void> {
    await this.db.query(
      `INSERT INTO retry_counters (case_id, category, root_cause, auto_revisions)
       VALUES ($1,$2,$3,$4)
       ON CONFLICT (case_id, category, root_cause)
       DO UPDATE SET auto_revisions = EXCLUDED.auto_revisions`,
      [record.case_id, record.category, record.root_cause, record.auto_revisions],
    );
  }

  async listRetryCounters(caseId: string): Promise<RetryCounterRecord[]> {
    const { rows } = await this.db.query(`SELECT * FROM retry_counters WHERE case_id=$1`, [
      caseId,
    ]);
    return rows.map((row) => ({
      case_id: row.case_id,
      category: row.category,
      root_cause: row.root_cause,
      auto_revisions: row.auto_revisions,
    }));
  }
}

export class PgStore extends PgSession implements Store {
  private readonly pool: Pool;

  constructor(connectionString: string) {
    const pool = new Pool({ connectionString });
    super(pool);
    this.pool = pool;
  }

  async transaction<T>(fn: (tx: StoreSession) => Promise<T>): Promise<T> {
    const client: PoolClient = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await fn(new PgSession(client));
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
