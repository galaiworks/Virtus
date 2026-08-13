/**
 * HITL 5 件(手順書 E-1「HITL統合」/ F-1 パイロット開始条件)。
 *
 * 権限外・期限切れ・二重操作・古いカード・条件付き承認の 5 ケースを、
 * サーバー側の再検証(D-3 手順 2-8)が確実に止めることを確認する。
 */

import { buildDeterministicApp, type App } from '../app.js';
import { FixedClock } from '../domain/clock.js';
import { SequentialIdGenerator } from '../domain/ids.js';
import { StaticIdentityResolver } from '../ports/identity.js';
import { MemoryChatAdapter } from '../adapters/chat/memory-chat.js';
import { buildIntake, EVAL_NOW, MEETING_MINUTES } from './fixtures.js';
import type { ApprovalRefusal } from '../approval/approval-service.js';

export interface HitlCaseResult {
  id: string;
  title: string;
  passed: boolean;
  failures: string[];
}

export interface HitlSuiteResult {
  total: number;
  passed: number;
  failed: number;
  results: HitlCaseResult[];
}

const IDENTITIES = {
  U_APPROVER: { userId: 'approver-1', displayName: '承認権者', role: 'approver' as const },
  U_REQUESTER: { userId: 'requester-1', displayName: '依頼者', role: 'requester' as const },
};

export interface HitlFixture {
  app: App;
  clock: FixedClock;
  chat: MemoryChatAdapter;
  caseId: string;
  requestId: string;
  cardVersion: number;
  nonce: string;
}

/** 顧客向けメール草案を承認待ちまで進めた状態を作る。 */
export async function setupAwaitingApproval(caseId = 'case_hitl'): Promise<HitlFixture> {
  const clock = new FixedClock(new Date(EVAL_NOW));
  const chat = new MemoryChatAdapter();
  const app = buildDeterministicApp({
    clock,
    chat,
    ids: new SequentialIdGenerator(),
    identities: new StaticIdentityResolver(IDENTITIES),
  });

  const intake = buildIntake(
    {
      case_id: caseId,
      desired_artifacts: ['weekly_report', 'email_draft'],
      permitted_operations: ['internal_draft.save', 'external_email.send'],
      permitted_personal_data: ['client@example.com'],
    },
    [{ source_id: `${caseId}_src`, title: '定例会議 議事録', content: MEETING_MINUTES }],
  );

  await app.orchestrator.intake(intake);
  const result = await app.orchestrator.run(caseId);
  const request = result.approvalRequests[0];
  if (!request) {
    throw new Error(`承認要求が作られていません(状態: ${result.state})`);
  }

  return {
    app,
    clock,
    chat,
    caseId,
    requestId: request.request_id,
    cardVersion: request.packet.card_version,
    nonce: request.packet.nonce,
  };
}

const approveInput = (conditions: string[] = []) => ({
  decision: conditions.length > 0 ? 'approved_with_conditions' : 'approved',
  reason: '内容を確認した',
  conditions,
  scope_override: null,
});

async function runCase(
  id: string,
  title: string,
  body: (record: (message: string) => void) => Promise<void>,
): Promise<HitlCaseResult> {
  const failures: string[] = [];
  try {
    await body((message) => failures.push(message));
  } catch (error) {
    failures.push(`例外: ${error instanceof Error ? error.message : String(error)}`);
  }
  return { id, title, passed: failures.length === 0, failures };
}

function expectRefusal(
  outcome: { ok: boolean; refusal?: ApprovalRefusal },
  expected: ApprovalRefusal,
  record: (message: string) => void,
): void {
  if (outcome.ok) {
    record(`拒否されるべき操作が通った(期待: ${expected})`);
    return;
  }
  if (outcome.refusal !== expected) {
    record(`拒否理由が異なる: 期待 ${expected} / 実際 ${outcome.refusal}`);
  }
}

export async function runHitlSuite(): Promise<HitlSuiteResult> {
  const results: HitlCaseResult[] = [];

  /* H01: 権限外の利用者が承認しようとする。 */
  results.push(
    await runCase('H01', '承認ロールを持たない利用者の操作を拒否する', async (record) => {
      const fx = await setupAwaitingApproval('case_hitl_01');
      const outcome = await fx.app.approvals.submitDecision({
        requestId: fx.requestId,
        platformUserId: 'U_REQUESTER',
        cardVersion: fx.cardVersion,
        nonce: fx.nonce,
        decision: approveInput(),
      });
      expectRefusal(outcome, 'forbidden_role', record);

      const jobs = await fx.app.store.listExecutionJobs(fx.caseId);
      if (jobs.length > 0) record('拒否されたのに実行ジョブが作られている');
      const decisions = await fx.app.store.listApprovalDecisions(fx.caseId);
      if (decisions.length > 0) record('拒否されたのに承認記録が作られている');

      const audit = await fx.app.store.listAuditEvents(fx.caseId);
      if (!audit.some((e) => e.event_type === 'approval.action_rejected')) {
        record('拒否が監査ログに残っていない');
      }
      await fx.app.close();
    }),
  );

  /* H02: 期限切れ。 */
  results.push(
    await runCase('H02', '期限切れの承認操作を拒否し、カードを期限切れにする', async (record) => {
      const fx = await setupAwaitingApproval('case_hitl_02');
      fx.clock.advance(25 * 60 * 60 * 1000);

      const outcome = await fx.app.approvals.submitDecision({
        requestId: fx.requestId,
        platformUserId: 'U_APPROVER',
        cardVersion: fx.cardVersion,
        nonce: fx.nonce,
        decision: approveInput(),
      });
      expectRefusal(outcome, 'expired', record);

      const request = await fx.app.store.getApprovalRequest(fx.requestId);
      if (request?.status !== 'expired') record(`承認要求が expired になっていない: ${request?.status}`);

      const card = fx.chat.find(fx.requestId);
      if (card?.finalState?.kind !== 'expired') record('カードが期限切れ表示に更新されていない');

      const jobs = await fx.app.store.listExecutionJobs(fx.caseId);
      if (jobs.length > 0) record('期限切れなのに実行ジョブが作られている');
      await fx.app.close();
    }),
  );

  /* H03: 二重操作。 */
  results.push(
    await runCase('H03', '同一カードからの二重操作を拒否する', async (record) => {
      const fx = await setupAwaitingApproval('case_hitl_03');

      const first = await fx.app.approvals.submitDecision({
        requestId: fx.requestId,
        platformUserId: 'U_APPROVER',
        cardVersion: fx.cardVersion,
        nonce: fx.nonce,
        decision: approveInput(),
      });
      if (!first.ok) record(`1 回目の承認が通らなかった: ${first.refusal}`);

      const second = await fx.app.approvals.submitDecision({
        requestId: fx.requestId,
        platformUserId: 'U_APPROVER',
        cardVersion: fx.cardVersion,
        nonce: fx.nonce,
        decision: approveInput(),
      });
      expectRefusal(second, 'already_processed', record);

      const decisions = await fx.app.store.listApprovalDecisions(fx.caseId);
      if (decisions.length !== 1) record(`承認記録が ${decisions.length} 件ある(1 件であるべき)`);

      const jobs = await fx.app.store.listExecutionJobs(fx.caseId);
      const emailJobs = jobs.filter((j) => j.operation === 'external_email.send');
      if (emailJobs.length !== 1) record(`メール操作のジョブが ${emailJobs.length} 件ある`);
      if (emailJobs[0]?.status !== 'handed_off_to_human') {
        record(`MVP では自動送信しないはずが status=${emailJobs[0]?.status}`);
      }
      await fx.app.close();
    }),
  );

  /* H04: 古いカード。 */
  results.push(
    await runCase('H04', '古いカードからの操作を拒否する', async (record) => {
      const fx = await setupAwaitingApproval('case_hitl_04');
      const outcome = await fx.app.approvals.submitDecision({
        requestId: fx.requestId,
        platformUserId: 'U_APPROVER',
        cardVersion: fx.cardVersion - 1,
        nonce: fx.nonce,
        decision: approveInput(),
      });
      expectRefusal(outcome, 'stale_card', record);

      const jobs = await fx.app.store.listExecutionJobs(fx.caseId);
      if (jobs.length > 0) record('拒否されたのに実行ジョブが作られている');
      await fx.app.close();
    }),
  );

  /* H05: 条件付き承認が scope を拡張している。 */
  results.push(
    await runCase('H05', '承認条件による scope 拡張を拒否する', async (record) => {
      const fx = await setupAwaitingApproval('case_hitl_05');
      const outcome = await fx.app.approvals.submitDecision({
        requestId: fx.requestId,
        platformUserId: 'U_APPROVER',
        cardVersion: fx.cardVersion,
        nonce: fx.nonce,
        decision: {
          decision: 'approved_with_conditions',
          reason: '宛先を追加して送ってほしい',
          conditions: ['宛先に another@example.com を追加する'],
          scope_override: null,
        },
      });
      expectRefusal(outcome, 'scope_expansion', record);

      const jobs = await fx.app.store.listExecutionJobs(fx.caseId);
      if (jobs.length > 0) record('拒否されたのに実行ジョブが作られている');

      const request = await fx.app.store.getApprovalRequest(fx.requestId);
      if (request?.status !== 'pending') record('拒否後も承認要求は pending のままであるべき');
      await fx.app.close();
    }),
  );

  const passed = results.filter((r) => r.passed).length;
  return { total: results.length, passed, failed: results.length - passed, results };
}
