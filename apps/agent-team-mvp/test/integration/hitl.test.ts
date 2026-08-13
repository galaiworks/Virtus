/**
 * HITL 統合(手順書 E-1)。
 *
 * 権限外、期限切れ、二重操作、古いカード、条件付き承認を確認する。
 * 併せて、正常な承認が「許可された scope だけ」を実行することを確認する。
 */

import { describe, expect, it } from 'vitest';
import { runHitlSuite, setupAwaitingApproval } from '../../src/eval/hitl-runner.js';

describe('HITL 5 ケース(F-1 パイロット開始条件)', () => {
  it('すべて合格する', async () => {
    const suite = await runHitlSuite();
    const failures = suite.results.filter((r) => !r.passed);
    expect(failures.map((f) => `${f.id}: ${f.failures.join(' / ')}`)).toEqual([]);
    expect(suite.passed).toBe(5);
  });
});

describe('承認の正常系', () => {
  it('承認すると許可 scope の操作と待機中の Green 操作だけが実行される', async () => {
    const fx = await setupAwaitingApproval('case_hitl_ok');

    const outcome = await fx.app.approvals.submitDecision({
      requestId: fx.requestId,
      platformUserId: 'U_APPROVER',
      cardVersion: fx.cardVersion,
      nonce: fx.nonce,
      decision: {
        decision: 'approved',
        reason: '内容を確認した',
        conditions: [],
        scope_override: null,
      },
    });

    expect(outcome.ok).toBe(true);
    if (!outcome.ok) return;

    const operations = outcome.executions.map((e) => e.operation).sort();
    expect(operations).toEqual(['external_email.send', 'internal_draft.save']);

    // 外部送信は MVP では自動実行せず、人間へ引き渡す。
    const email = outcome.executions.find((e) => e.operation === 'external_email.send');
    expect(email?.status).toBe('handed_off_to_human');
    expect(email?.approval_request_id).toBe(fx.requestId);

    const internal = outcome.executions.find((e) => e.operation === 'internal_draft.save');
    expect(internal?.status).toBe('succeeded');

    const caseRecord = await fx.app.store.getCase(fx.caseId);
    expect(caseRecord?.state).toBe('pass');
    expect(caseRecord?.stage).toBe('closed');

    const card = fx.chat.find(fx.requestId);
    expect(card?.finalState?.kind).toBe('approved');
    await fx.app.close();
  });

  it('差戻しでは何も実行されず、カードが差戻し表示になる', async () => {
    const fx = await setupAwaitingApproval('case_hitl_return');

    const outcome = await fx.app.approvals.submitDecision({
      requestId: fx.requestId,
      platformUserId: 'U_APPROVER',
      cardVersion: fx.cardVersion,
      nonce: fx.nonce,
      decision: {
        decision: 'returned',
        reason: '根拠が不足している',
        conditions: [],
        scope_override: null,
      },
    });

    expect(outcome.ok).toBe(true);
    if (outcome.ok) expect(outcome.executions).toHaveLength(0);
    expect(await fx.app.store.listExecutionJobs(fx.caseId)).toHaveLength(0);

    const card = fx.chat.find(fx.requestId);
    expect(card?.finalState?.kind).toBe('returned');
    await fx.app.close();
  });

  it('承認記録には決定者・理由・許可 scope・時刻が残る(FR-042)', async () => {
    const fx = await setupAwaitingApproval('case_hitl_audit');

    await fx.app.approvals.submitDecision({
      requestId: fx.requestId,
      platformUserId: 'U_APPROVER',
      cardVersion: fx.cardVersion,
      nonce: fx.nonce,
      decision: {
        decision: 'approved',
        reason: '確認済み',
        conditions: [],
        scope_override: null,
      },
    });

    const decisions = await fx.app.store.listApprovalDecisions(fx.caseId);
    expect(decisions).toHaveLength(1);
    const decision = decisions[0]!;
    expect(decision.decided_by).toBe('approver-1');
    expect(decision.decided_by_role).toBe('approver');
    expect(decision.reason).toBe('確認済み');
    expect(decision.granted_scope.recipients).toEqual(['client@example.com']);
    expect(decision.decided_at).toBeTruthy();

    const audit = await fx.app.store.listAuditEvents(fx.caseId);
    const approvalEvent = audit.find((e) => e.event_type === 'approval.decided');
    expect(approvalEvent?.approval_request_id).toBe(fx.requestId);
    expect(approvalEvent?.actor).toBe('approver-1');
    await fx.app.close();
  });
});

describe('カードの中身(FR-031)', () => {
  it('カードには秘密情報も、案件が許可していない個人情報も載らない', async () => {
    const fx = await setupAwaitingApproval('case_hitl_card');
    const card = fx.chat.find(fx.requestId);
    expect(card).toBeDefined();

    const serialized = JSON.stringify(card);
    expect(serialized).not.toContain('sk-');
    expect(serialized).not.toContain('xoxb-');
    // 許可された宛先は載ってよいが、それ以外のメールアドレスは載らない。
    const emails = serialized.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) ?? [];
    expect(new Set(emails)).toEqual(new Set(['client@example.com']));
    await fx.app.close();
  });

  it('承認要求には期限・冪等性キー・ロールバックが必ず含まれる(FR-023)', async () => {
    const fx = await setupAwaitingApproval('case_hitl_packet');
    const request = await fx.app.store.getApprovalRequest(fx.requestId);
    const packet = request!.packet;

    expect(new Date(packet.expires_at).getTime()).toBeGreaterThan(fx.clock.now().getTime());
    expect(packet.idempotency_key).toMatch(/^idem_/);
    expect(packet.rollback.length).toBeGreaterThan(0);
    expect(packet.constraints.length).toBeGreaterThan(0);
    expect(packet.required_role).toBe('approver');
    await fx.app.close();
  });
});
