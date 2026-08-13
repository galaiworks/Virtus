/**
 * ユニット: 自動差戻しの上限(FR-022)。
 *
 * 同一カテゴリ・同一根本原因の自動差戻しは 2 回まで。
 * 3 回目は human_review_required とし、4 回目の自動差戻しは発生しない。
 */

import { describe, expect, it } from 'vitest';
import { MemoryStore } from '../../src/adapters/store/memory-store.js';
import { evaluateRetryBudget, MAX_AUTO_REVISIONS } from '../../src/workflow/retry-policy.js';
import type { QaFinding } from '../../src/domain/schemas.js';

const finding = (rootCause: string, category: QaFinding['category'] = 'revision'): QaFinding => ({
  category,
  root_cause: rootCause,
  severity: 'blocker',
  detail: `${rootCause} の指摘`,
  target: null,
});

async function seedCase(store: MemoryStore, caseId: string): Promise<void> {
  await store.insertCase({
    case_id: caseId,
    objective: 'テスト',
    due_date: '2026-08-20',
    desired_artifacts: [],
    target_workflow: null,
    business_owner: 'owner',
    approver: 'approver',
    permitted_operations: [],
    permitted_personal_data: [],
    actor_roles: ['ai_ops'],
    state: 'needs_revision',
    stage: 'qa',
    risk: 'green',
    created_at: '2026-08-13T00:00:00.000Z',
    updated_at: '2026-08-13T00:00:00.000Z',
  });
}

describe('自動差戻しの上限', () => {
  it('上限は 2 回', () => {
    expect(MAX_AUTO_REVISIONS).toBe(2);
  });

  it('3 回目の検出で自動差戻しを止める', async () => {
    const store = new MemoryStore();
    await seedCase(store, 'case_r1');
    const findings = [finding('missing_evidence')];

    const first = await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r1', findings));
    expect(first.allowAutoRevision).toBe(true);

    const second = await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r1', findings));
    expect(second.allowAutoRevision).toBe(true);

    const third = await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r1', findings));
    expect(third.allowAutoRevision).toBe(false);
    expect(third.exhausted?.root_cause).toBe('missing_evidence');
    expect(third.exhausted?.auto_revisions).toBe(2);

    // 4 回目も許可されない。
    const fourth = await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r1', findings));
    expect(fourth.allowAutoRevision).toBe(false);
  });

  it('同一原因の指摘が複数あっても 1 回として数える', async () => {
    const store = new MemoryStore();
    await seedCase(store, 'case_r2');
    const findings = [finding('missing_evidence'), finding('missing_evidence'), finding('missing_evidence')];

    await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r2', findings));
    const counters = await store.listRetryCounters('case_r2');
    expect(counters).toHaveLength(1);
    expect(counters[0]?.auto_revisions).toBe(1);
  });

  it('根本原因が異なればカウンタは独立する', async () => {
    const store = new MemoryStore();
    await seedCase(store, 'case_r3');

    await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r3', [finding('missing_evidence')]));
    await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r3', [finding('missing_evidence')]));

    const other = await store.transaction((tx) =>
      evaluateRetryBudget(tx, 'case_r3', [finding('empty_document')]),
    );
    expect(other.allowAutoRevision).toBe(true);

    const same = await store.transaction((tx) =>
      evaluateRetryBudget(tx, 'case_r3', [finding('missing_evidence')]),
    );
    expect(same.allowAutoRevision).toBe(false);
  });

  it('指摘が無ければ自動差戻ししない', async () => {
    const store = new MemoryStore();
    await seedCase(store, 'case_r4');
    const result = await store.transaction((tx) => evaluateRetryBudget(tx, 'case_r4', []));
    expect(result.allowAutoRevision).toBe(false);
  });
});
