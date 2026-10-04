/**
 * チャット統合(手順書 E-1「HITL統合」/ D-3)。
 *
 * カードが返す値をそのまま実行しないこと、
 * 署名検証を通らない操作が実行されないことを、HTTP 層込みで確認する。
 */

import { createHmac } from 'node:crypto';
import { afterEach, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { buildApp, type App } from '../../src/app.js';
import { buildServer } from '../../src/api/server.js';
import { MemoryStore } from '../../src/adapters/store/memory-store.js';
import { ScriptedLlmAdapter } from '../../src/adapters/llm/scripted-llm.js';
import { SlackChatAdapter, type SlackClient } from '../../src/adapters/chat/slack-adapter.js';
import { StaticIdentityResolver } from '../../src/ports/identity.js';
import { FixedClock } from '../../src/domain/clock.js';
import { SequentialIdGenerator } from '../../src/domain/ids.js';
import { buildIntake, EVAL_NOW, MEETING_MINUTES } from '../../src/eval/fixtures.js';

const SIGNING_SECRET = 'test-signing-secret';

class FakeSlackClient implements SlackClient {
  readonly posted: { channel: string; text: string; blocks: unknown[] }[] = [];
  readonly updated: { channel: string; ts: string; text: string }[] = [];
  readonly views: unknown[] = [];
  private counter = 0;

  async postMessage(args: { channel: string; text: string; blocks: unknown[] }) {
    this.posted.push(args);
    this.counter += 1;
    return { ts: `168000000.${this.counter}` };
  }

  async updateMessage(args: { channel: string; ts: string; text: string; blocks: unknown[] }) {
    this.updated.push(args);
  }

  async openView(args: { triggerId: string; view: unknown }) {
    this.views.push(args.view);
  }
}

interface Fixture {
  app: App;
  server: FastifyInstance;
  slack: FakeSlackClient;
  clock: FixedClock;
  caseId: string;
  requestId: string;
  cardVersion: number;
}

const fixtures: Fixture[] = [];

async function setup(caseId: string): Promise<Fixture> {
  const clock = new FixedClock(new Date(EVAL_NOW));
  const slack = new FakeSlackClient();
  const app = buildApp({
    clock,
    ids: new SequentialIdGenerator(),
    store: new MemoryStore(),
    llm: new ScriptedLlmAdapter(),
    chat: new SlackChatAdapter(slack, 'https://admin.example.com'),
    identities: new StaticIdentityResolver({
      U_APPROVER: { userId: 'approver-1', displayName: '承認権者', role: 'approver' },
      U_REQUESTER: { userId: 'requester-1', displayName: '依頼者', role: 'requester' },
    }),
    config: {
      store: 'memory',
      databaseUrl: null,
      llm: { provider: 'scripted', apiKey: null, model: 'scripted' },
      chat: {
        provider: 'slack',
        slack: {
          botToken: 'xoxb-test',
          signingSecret: SIGNING_SECRET,
          approvalChannel: '#approvals',
        },
      },
    },
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
  if (!request) throw new Error('承認要求が作られていません');

  const fixture: Fixture = {
    app,
    server: buildServer(app),
    slack,
    clock,
    caseId,
    requestId: request.request_id,
    cardVersion: request.packet.card_version,
  };
  fixtures.push(fixture);
  return fixture;
}

afterEach(async () => {
  while (fixtures.length > 0) {
    const fixture = fixtures.pop()!;
    await fixture.server.close();
    await fixture.app.close();
  }
});

function post(fixture: Fixture, payload: unknown, options?: { secret?: string; skew?: number }) {
  const rawBody = new URLSearchParams({ payload: JSON.stringify(payload) }).toString();
  const timestamp = fixture.clock.unixSeconds() + (options?.skew ?? 0);
  const signature = `v0=${createHmac('sha256', options?.secret ?? SIGNING_SECRET)
    .update(`v0:${timestamp}:${rawBody}`)
    .digest('hex')}`;

  return fixture.server.inject({
    method: 'POST',
    url: '/slack/interactions',
    headers: {
      'content-type': 'application/x-www-form-urlencoded',
      'x-slack-request-timestamp': String(timestamp),
      'x-slack-signature': signature,
    },
    payload: rawBody,
  });
}

const openDetailsPayload = (fixture: Fixture, userId = 'U_APPROVER') => ({
  type: 'block_actions',
  user: { id: userId },
  trigger_id: 'trigger-1',
  actions: [
    {
      action_id: 'approval_open_details',
      value: JSON.stringify({ request_id: fixture.requestId, card_version: fixture.cardVersion }),
    },
  ],
});

describe('署名検証(FR-034)', () => {
  it('正規のリクエストだけを処理する', async () => {
    const fixture = await setup('case_w1');
    const response = await post(fixture, openDetailsPayload(fixture));
    expect(response.statusCode).toBe(200);
    expect(fixture.slack.views).toHaveLength(1);
  });

  it('署名が合わないリクエストは 401 で拒否し、モーダルも開かない', async () => {
    const fixture = await setup('case_w2');
    const response = await post(fixture, openDetailsPayload(fixture), { secret: 'wrong-secret' });
    expect(response.statusCode).toBe(401);
    expect(fixture.slack.views).toHaveLength(0);
  });

  it('古いタイムスタンプのリクエストは拒否する', async () => {
    const fixture = await setup('case_w3');
    const response = await post(fixture, openDetailsPayload(fixture), { skew: -60 * 10 });
    expect(response.statusCode).toBe(401);
    expect(fixture.slack.views).toHaveLength(0);
  });
});

describe('ボタン押下は最終承認ではない(FR-032)', () => {
  it('承認ロールが無ければモーダルを開かない', async () => {
    const fixture = await setup('case_w4');
    const response = await post(fixture, openDetailsPayload(fixture, 'U_REQUESTER'));
    expect(response.statusCode).toBe(200);
    expect(fixture.slack.views).toHaveLength(0);
    expect(response.json()).toMatchObject({ text: expect.stringContaining('承認ロール') });
  });

  it('カードのボタン値にはワンタイム値も実行権限も含まれない', async () => {
    const fixture = await setup('case_w5');
    const card = fixture.slack.posted[0]!;
    const serialized = JSON.stringify(card.blocks);
    const request = await fixture.app.store.getApprovalRequest(fixture.requestId);

    expect(serialized).toContain(fixture.requestId);
    expect(serialized).not.toContain(request!.packet.nonce);
    expect(serialized).not.toContain('xoxb-');
    // トップレベル text にもリスク・期限・操作を書く(アクセシビリティ)。
    expect(card.text).toContain('リスク');
    expect(card.text).toContain('期限');
  });

  it('モーダルを開いたときに初めてワンタイム値が渡る', async () => {
    const fixture = await setup('case_w6');
    await post(fixture, openDetailsPayload(fixture));
    const view = fixture.slack.views[0] as { private_metadata: string };
    const metadata = JSON.parse(view.private_metadata);
    const request = await fixture.app.store.getApprovalRequest(fixture.requestId);

    expect(metadata.request_id).toBe(fixture.requestId);
    expect(metadata.nonce).toBe(request!.packet.nonce);
    // モーダルを開いただけでは nonce を消費しない。
    expect(request!.nonce_consumed).toBe(false);
    expect(request!.status).toBe('pending');
  });
});

describe('判断 → 最終確認 → 確定(D-2 ステップ 3-4)', () => {
  async function openModal(fixture: Fixture): Promise<{ nonce: string }> {
    await post(fixture, openDetailsPayload(fixture));
    const view = fixture.slack.views[0] as { private_metadata: string };
    return JSON.parse(view.private_metadata);
  }

  const decisionSubmission = (fixture: Fixture, nonce: string, decision = 'approved') => ({
    type: 'view_submission',
    user: { id: 'U_APPROVER' },
    view: {
      callback_id: 'approval_decision_modal',
      private_metadata: JSON.stringify({
        request_id: fixture.requestId,
        card_version: fixture.cardVersion,
        nonce,
      }),
      state: {
        values: {
          decision: { value: { selected_option: { value: decision } } },
          reason: { value: { value: '内容を確認した' } },
          conditions: { value: { value: '' } },
        },
      },
    },
  });

  it('判断フォームの送信では確定せず、最終確認画面を返す', async () => {
    const fixture = await setup('case_w7');
    const { nonce } = await openModal(fixture);

    const response = await post(fixture, decisionSubmission(fixture, nonce));
    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({ response_action: 'push' });

    // まだ承認は記録されていない。
    expect(await fixture.app.store.listApprovalDecisions(fixture.caseId)).toHaveLength(0);
    expect(await fixture.app.store.listExecutionJobs(fixture.caseId)).toHaveLength(0);
  });

  it('理由が空なら最終確認へ進めない', async () => {
    const fixture = await setup('case_w8');
    const { nonce } = await openModal(fixture);
    const submission = decisionSubmission(fixture, nonce);
    submission.view.state.values.reason.value.value = '';

    const response = await post(fixture, submission);
    expect(response.json()).toMatchObject({ response_action: 'errors' });
  });

  it('最終確定で初めて承認が記録され、許可 scope だけが実行される', async () => {
    const fixture = await setup('case_w9');
    const { nonce } = await openModal(fixture);

    const pushed = await post(fixture, decisionSubmission(fixture, nonce));
    const confirmView = (pushed.json() as { view: { private_metadata: string } }).view;

    const response = await post(fixture, {
      type: 'view_submission',
      user: { id: 'U_APPROVER' },
      view: {
        callback_id: 'approval_confirm_modal',
        private_metadata: confirmView.private_metadata,
      },
    });

    expect(response.json()).toMatchObject({ response_action: 'clear' });

    const decisions = await fixture.app.store.listApprovalDecisions(fixture.caseId);
    expect(decisions).toHaveLength(1);
    expect(decisions[0]?.decided_by).toBe('approver-1');

    const jobs = await fixture.app.store.listExecutionJobs(fixture.caseId);
    expect(jobs.map((j) => j.operation).sort()).toEqual([
      'external_email.send',
      'internal_draft.save',
    ]);
    expect(jobs.find((j) => j.operation === 'external_email.send')?.status).toBe(
      'handed_off_to_human',
    );

    // 元カードが最終状態に更新される(FR-033)。
    expect(fixture.slack.updated).toHaveLength(1);
    expect(fixture.slack.updated[0]?.text).toContain('承認済み');
  });

  it('確定後に同じカードから再送しても処理されない(FR-033)', async () => {
    const fixture = await setup('case_w10');
    const { nonce } = await openModal(fixture);
    const pushed = await post(fixture, decisionSubmission(fixture, nonce));
    const confirmView = (pushed.json() as { view: { private_metadata: string } }).view;

    const confirm = {
      type: 'view_submission',
      user: { id: 'U_APPROVER' },
      view: {
        callback_id: 'approval_confirm_modal',
        private_metadata: confirmView.private_metadata,
      },
    };

    await post(fixture, confirm);
    const second = await post(fixture, confirm);

    expect(second.json()).toMatchObject({ response_action: 'errors' });
    expect(await fixture.app.store.listApprovalDecisions(fixture.caseId)).toHaveLength(1);
  });
});
