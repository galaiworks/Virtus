/**
 * 限定実行(FR-040 / FR-041)。
 *
 * 実行前に次を必ず確認する。
 * 1. 案件が許可した操作か
 * 2. Green かつ可逆かつ MVP 自動実行対象か。そうでなければ承認記録を要求する
 * 3. 承認 scope と実行 scope が一致するか
 * 4. 冪等性キーで既に実行済みでないか
 *
 * どれか 1 つでも満たさない場合は実行しない。
 */

import type { StoreSession } from '../ports/store.js';
import type { ExecutionAdapter } from '../ports/execution.js';
import type { CaseRecord, ExecutionJobRecord } from '../domain/types.js';
import { isGreenAutoExecutable, operationSpec, type OperationId } from '../domain/risk.js';
import type { IdGenerator } from '../domain/ids.js';
import type { Clock } from '../domain/clock.js';
import type { AuditRecorder } from '../audit/audit-log.js';

export interface ExecutionRequest {
  caseRecord: CaseRecord;
  operation: OperationId;
  target: string;
  payload: Record<string, unknown>;
  idempotencyKey: string;
  /** Yellow/Red の場合は必須。 */
  approvalRequestId?: string | null;
  /** 承認で許可された scope。実行 scope がこれを超えてはならない。 */
  approvedScope?: { operation: OperationId; target: string; recipients: readonly string[] } | null;
}

export type ExecutionRefusal =
  | 'operation_not_permitted'
  | 'approval_required'
  | 'scope_mismatch'
  | 'no_adapter';

export type ExecutionResult =
  | { ok: true; job: ExecutionJobRecord; duplicate: boolean }
  | { ok: false; refusal: ExecutionRefusal; message: string }
  | { ok: false; refusal: 'execution_failed'; message: string; job: ExecutionJobRecord };

export class ExecutionRunner {
  constructor(
    private readonly adapters: readonly ExecutionAdapter[],
    private readonly ids: IdGenerator,
    private readonly clock: Clock,
    private readonly audit: AuditRecorder,
  ) {}

  async run(tx: StoreSession, request: ExecutionRequest): Promise<ExecutionResult> {
    const { caseRecord, operation } = request;

    /* 1. 案件が許可した操作か。 */
    if (!caseRecord.permitted_operations.includes(operation)) {
      await this.audit.record(tx, {
        case_id: caseRecord.case_id,
        event_type: 'execution.attempted',
        actor: 'execution_runner',
        actor_role: 'system',
        decision: 'refused:operation_not_permitted',
        detail: { operation },
      });
      return {
        ok: false,
        refusal: 'operation_not_permitted',
        message: `案件が許可していない操作: ${operation}`,
      };
    }

    /* 2. 承認の要否。Green 以外は承認記録なしに実行しない。 */
    if (!isGreenAutoExecutable(operation)) {
      if (!request.approvalRequestId || !request.approvedScope) {
        await this.audit.record(tx, {
          case_id: caseRecord.case_id,
          event_type: 'execution.attempted',
          actor: 'execution_runner',
          actor_role: 'system',
          decision: 'refused:approval_required',
          detail: { operation, risk: operationSpec(operation).risk },
        });
        return {
          ok: false,
          refusal: 'approval_required',
          message: `${operation} は承認記録なしに実行できない`,
        };
      }

      /* 3. 承認 scope と実行 scope の一致。 */
      const scope = request.approvedScope;
      const recipients = extractRecipients(request.payload);
      const scopeOk =
        scope.operation === operation &&
        scope.target === request.target &&
        recipients.every((r) => scope.recipients.includes(r));
      if (!scopeOk) {
        await this.audit.record(tx, {
          case_id: caseRecord.case_id,
          event_type: 'execution.attempted',
          actor: 'execution_runner',
          actor_role: 'system',
          approval_request_id: request.approvalRequestId,
          decision: 'refused:scope_mismatch',
          detail: { operation, target: request.target, approved_target: scope.target },
        });
        return {
          ok: false,
          refusal: 'scope_mismatch',
          message: '承認された scope と実行 scope が一致しない',
        };
      }
    }

    /* 4. 冪等性。既に実行済みなら再実行しない。 */
    const existing = await tx.findExecutionByIdempotencyKey(request.idempotencyKey);
    if (existing) {
      await this.audit.record(tx, {
        case_id: caseRecord.case_id,
        event_type: 'execution.attempted',
        actor: 'execution_runner',
        actor_role: 'system',
        execution_id: existing.execution_id,
        decision: 'skipped_duplicate',
        detail: { idempotency_key: request.idempotencyKey },
      });
      return { ok: true, job: existing, duplicate: true };
    }

    const adapter = this.adapters.find((a) => a.supports(operation));
    if (!adapter) {
      return { ok: false, refusal: 'no_adapter', message: `実行アダプタが無い: ${operation}` };
    }

    const outcome = await adapter.execute({
      case_id: caseRecord.case_id,
      operation,
      target: request.target,
      payload: request.payload,
      idempotency_key: request.idempotencyKey,
    });

    const job: ExecutionJobRecord = {
      execution_id: this.ids.next('job'),
      case_id: caseRecord.case_id,
      operation,
      target: request.target,
      idempotency_key: request.idempotencyKey,
      status:
        outcome.status === 'succeeded'
          ? 'succeeded'
          : outcome.status === 'handed_off_to_human'
            ? 'handed_off_to_human'
            : 'failed',
      result: outcome.status === 'failed' ? '' : outcome.result,
      rollback_ref: outcome.status === 'succeeded' ? outcome.rollbackRef : null,
      approval_request_id: request.approvalRequestId ?? null,
      attempt: 1,
      error: outcome.status === 'failed' ? outcome.error : null,
      executed_at: this.clock.now().toISOString(),
    };
    await tx.insertExecutionJob(job);

    await this.audit.record(tx, {
      case_id: caseRecord.case_id,
      event_type: 'execution.completed',
      actor: adapter.name,
      actor_role: 'system',
      execution_id: job.execution_id,
      approval_request_id: job.approval_request_id,
      decision: job.status,
      detail: { operation, target: request.target, rollback_ref: job.rollback_ref },
    });

    if (outcome.status === 'failed') {
      return {
        ok: false,
        refusal: 'execution_failed',
        message: outcome.error,
        job,
      };
    }

    return { ok: true, job, duplicate: false };
  }
}

function extractRecipients(payload: Record<string, unknown>): string[] {
  const to = payload.to;
  if (Array.isArray(to)) return to.filter((v): v is string => typeof v === 'string');
  return [];
}
