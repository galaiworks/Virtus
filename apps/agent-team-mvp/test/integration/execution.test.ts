/**
 * 実行統合(手順書 E-1)。
 *
 * 冪等性、部分成功、承認なし実行の拒否、ロールバック参照を確認する。
 */

import { describe, expect, it } from 'vitest';
import { MemoryStore } from '../../src/adapters/store/memory-store.js';
import { SequentialIdGenerator } from '../../src/domain/ids.js';
import { FixedClock } from '../../src/domain/clock.js';
import { AuditRecorder } from '../../src/audit/audit-log.js';
import { ExecutionRunner } from '../../src/execution/execution-runner.js';
import {
  InternalExecutionAdapter,
  ManualHandoffAdapter,
} from '../../src/adapters/execution/internal-execution.js';
import type { CaseRecord } from '../../src/domain/types.js';
import type { ExecutionAdapter } from '../../src/ports/execution.js';
import { EVAL_NOW } from '../../src/eval/fixtures.js';

const CASE: CaseRecord = {
  case_id: 'case_x1',
  objective: 'テスト',
  due_date: '2026-08-20',
  desired_artifacts: ['weekly_report'],
  target_workflow: 'weekly_report',
  business_owner: 'owner-1',
  approver: 'approver-1',
  permitted_operations: ['internal_draft.save', 'external_email.send'],
  permitted_personal_data: ['client@example.com'],
  actor_roles: ['ai_ops'],
  state: 'pass',
  stage: 'execution',
  risk: 'green',
  created_at: '2026-08-13T00:00:00.000Z',
  updated_at: '2026-08-13T00:00:00.000Z',
};

function makeRunner(adapters?: ExecutionAdapter[]) {
  const store = new MemoryStore();
  const ids = new SequentialIdGenerator();
  const clock = new FixedClock(new Date(EVAL_NOW));
  const audit = new AuditRecorder(ids, clock);
  const internal = new InternalExecutionAdapter(() => clock.now());
  const runner = new ExecutionRunner(
    adapters ?? [internal, new ManualHandoffAdapter()],
    ids,
    clock,
    audit,
  );
  return { store, runner, internal };
}

async function seed(store: MemoryStore): Promise<void> {
  await store.insertCase(CASE);
}

describe('冪等性(FR-041)', () => {
  it('同じ冪等性キーの操作は二重に実行されない', async () => {
    const { store, runner, internal } = makeRunner();
    await seed(store);

    const request = {
      caseRecord: CASE,
      operation: 'internal_draft.save' as const,
      target: 'case_x1/weekly_report',
      payload: { document: { title: '週報' } },
      idempotencyKey: 'idem_same',
    };

    const first = await store.transaction((tx) => runner.run(tx, request));
    const second = await store.transaction((tx) => runner.run(tx, request));

    expect(first.ok).toBe(true);
    expect(second.ok).toBe(true);
    if (first.ok && second.ok) {
      expect(first.duplicate).toBe(false);
      expect(second.duplicate).toBe(true);
      expect(second.job.execution_id).toBe(first.job.execution_id);
    }

    expect(await store.listExecutionJobs('case_x1')).toHaveLength(1);
    // 実際の保存も 1 回だけ。
    expect(internal.list('case_x1')).toHaveLength(1);
  });

  it('成功した実行にはロールバック参照が残る', async () => {
    const { store, runner } = makeRunner();
    await seed(store);
    const outcome = await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'internal_draft.save',
        target: 'case_x1/weekly_report',
        payload: {},
        idempotencyKey: 'idem_rollback',
      }),
    );
    expect(outcome.ok).toBe(true);
    if (outcome.ok) {
      expect(outcome.job.rollback_ref).toBeTruthy();
      expect(outcome.job.status).toBe('succeeded');
    }
  });
});

describe('承認なし実行の拒否(G3)', () => {
  it('Yellow の操作は承認記録なしに実行できない', async () => {
    const { store, runner } = makeRunner();
    await seed(store);

    const outcome = await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'external_email.send',
        target: 'client@example.com',
        payload: { to: ['client@example.com'] },
        idempotencyKey: 'idem_email',
      }),
    );

    expect(outcome.ok).toBe(false);
    if (!outcome.ok) expect(outcome.refusal).toBe('approval_required');
    expect(await store.listExecutionJobs('case_x1')).toHaveLength(0);
  });

  it('承認 scope を超える宛先は実行しない', async () => {
    const { store, runner } = makeRunner();
    await seed(store);

    const outcome = await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'external_email.send',
        target: 'client@example.com',
        payload: { to: ['client@example.com', 'other@example.com'] },
        idempotencyKey: 'idem_scope',
        approvalRequestId: 'req_1',
        approvedScope: {
          operation: 'external_email.send',
          target: 'client@example.com',
          recipients: ['client@example.com'],
        },
      }),
    );

    expect(outcome.ok).toBe(false);
    if (!outcome.ok) expect(outcome.refusal).toBe('scope_mismatch');
  });

  it('承認済みでも MVP では外部送信せず人間へ引き渡す(要件定義 §2)', async () => {
    const { store, runner } = makeRunner();
    await seed(store);

    const outcome = await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'external_email.send',
        target: 'client@example.com',
        payload: { to: ['client@example.com'] },
        idempotencyKey: 'idem_handoff',
        approvalRequestId: 'req_1',
        approvedScope: {
          operation: 'external_email.send',
          target: 'client@example.com',
          recipients: ['client@example.com'],
        },
      }),
    );

    expect(outcome.ok).toBe(true);
    if (outcome.ok) expect(outcome.job.status).toBe('handed_off_to_human');
  });

  it('案件が許可していない操作は実行しない', async () => {
    const { store, runner } = makeRunner();
    await seed(store);

    const outcome = await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'storage.delete',
        target: 'src_1',
        payload: {},
        idempotencyKey: 'idem_delete',
      }),
    );

    expect(outcome.ok).toBe(false);
    if (!outcome.ok) expect(outcome.refusal).toBe('operation_not_permitted');
  });
});

describe('部分成功と失敗', () => {
  it('失敗した実行は記録され、冪等性キーは再試行のために解放される', async () => {
    const failing: ExecutionAdapter = {
      name: 'failing',
      supports: () => true,
      execute: async () => ({ status: 'failed', error: '保存先が応答しない', retryable: true }),
    };
    const { store, runner } = makeRunner([failing]);
    await seed(store);

    const request = {
      caseRecord: CASE,
      operation: 'internal_draft.save' as const,
      target: 'case_x1/weekly_report',
      payload: {},
      idempotencyKey: 'idem_fail',
    };

    const first = await store.transaction((tx) => runner.run(tx, request));
    expect(first.ok).toBe(false);
    if (!first.ok && first.refusal === 'execution_failed') {
      expect(first.job.status).toBe('failed');
      expect(first.job.error).toContain('保存先');
    }

    // 失敗は冪等性の対象外。再試行できる。
    const retry = await store.transaction((tx) => runner.run(tx, request));
    expect(retry.ok).toBe(false);
    expect(await store.listExecutionJobs('case_x1')).toHaveLength(2);
  });

  it('実行結果と拒否はすべて監査ログに残る', async () => {
    const { store, runner } = makeRunner();
    await seed(store);

    await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'external_email.send',
        target: 'client@example.com',
        payload: {},
        idempotencyKey: 'idem_audit_1',
      }),
    );
    await store.transaction((tx) =>
      runner.run(tx, {
        caseRecord: CASE,
        operation: 'internal_draft.save',
        target: 'case_x1/weekly_report',
        payload: {},
        idempotencyKey: 'idem_audit_2',
      }),
    );

    const audit = await store.listAuditEvents('case_x1');
    const decisions = audit.map((e) => e.decision);
    expect(decisions).toContain('refused:approval_required');
    expect(decisions).toContain('succeeded');
  });
});

describe('トランザクション', () => {
  it('例外が起きた一貫性単位の書き込みはすべて破棄される', async () => {
    const store = new MemoryStore();
    await seed(store);

    await expect(
      store.transaction(async (tx) => {
        await tx.insertExecutionJob({
          execution_id: 'job_tmp',
          case_id: 'case_x1',
          operation: 'internal_draft.save',
          target: 't',
          idempotency_key: 'k',
          status: 'succeeded',
          result: 'ok',
          rollback_ref: null,
          approval_request_id: null,
          attempt: 1,
          error: null,
          executed_at: '2026-08-13T00:00:00.000Z',
        });
        throw new Error('途中で失敗');
      }),
    ).rejects.toThrow('途中で失敗');

    expect(await store.listExecutionJobs('case_x1')).toHaveLength(0);
  });
});
