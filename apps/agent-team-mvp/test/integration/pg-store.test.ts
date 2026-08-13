/**
 * PostgreSQL アダプタの統合テスト。
 *
 * DATABASE_URL が設定されているときだけ実行する。
 *
 *   DATABASE_URL=postgres://... npm run migrate
 *   DATABASE_URL=postgres://... npx vitest run test/integration/pg-store.test.ts
 *
 * 確認するのは、スキーマとの往復、承認の原子的な確保(FR-033)、
 * 冪等性キーの一意性(FR-041)、監査の時系列(FR-042)。
 */

import { afterAll, beforeEach, describe, expect, it } from 'vitest';
import { Client } from 'pg';
import { PgStore } from '../../src/adapters/store/pg-store.js';
import { buildApp, type App } from '../../src/app.js';
import { ScriptedLlmAdapter } from '../../src/adapters/llm/scripted-llm.js';
import { MemoryChatAdapter } from '../../src/adapters/chat/memory-chat.js';
import { StaticIdentityResolver } from '../../src/ports/identity.js';
import { FixedClock } from '../../src/domain/clock.js';
import { RandomIdGenerator } from '../../src/domain/ids.js';
import { buildIntake, EVAL_NOW, MEETING_MINUTES } from '../../src/eval/fixtures.js';

const DATABASE_URL = process.env.DATABASE_URL;

describe.skipIf(!DATABASE_URL)('PostgreSQL Store', () => {
  let app: App;
  let chat: MemoryChatAdapter;
  let clock: FixedClock;
  let caseId: string;

  beforeEach(async () => {
    // 各テストで独立した case_id を使い、前のデータと衝突させない。
    caseId = `case_pg_${Date.now()}_${Math.floor(Math.random() * 1_000_000)}`;
    clock = new FixedClock(new Date(EVAL_NOW));
    chat = new MemoryChatAdapter();
    app = buildApp({
      clock,
      chat,
      ids: new RandomIdGenerator(),
      store: new PgStore(DATABASE_URL as string),
      llm: new ScriptedLlmAdapter(),
      identities: new StaticIdentityResolver({
        U_APPROVER: { userId: 'approver-1', displayName: '承認権者', role: 'approver' },
        U_REQUESTER: { userId: 'requester-1', displayName: '依頼者', role: 'requester' },
      }),
      config: {
        store: 'postgres',
        databaseUrl: DATABASE_URL,
        llm: { provider: 'scripted', apiKey: null, model: 'scripted' },
        chat: {
          provider: 'memory',
          slack: { botToken: null, signingSecret: null, approvalChannel: '#approvals' },
        },
      },
    });
  });

  afterAll(async () => {
    await app?.close();
  });

  async function runGreenCase(): Promise<void> {
    await app.orchestrator.intake(
      buildIntake({ case_id: caseId }, [
        { source_id: `${caseId}_src`, title: '定例会議 議事録', content: MEETING_MINUTES },
      ]),
    );
    await app.orchestrator.run(caseId);
  }

  async function runApprovalCase() {
    await app.orchestrator.intake(
      buildIntake(
        {
          case_id: caseId,
          desired_artifacts: ['weekly_report', 'email_draft'],
          permitted_operations: ['internal_draft.save', 'external_email.send'],
          permitted_personal_data: ['client@example.com'],
        },
        [{ source_id: `${caseId}_src`, title: '定例会議 議事録', content: MEETING_MINUTES }],
      ),
    );
    const result = await app.orchestrator.run(caseId);
    const request = result.approvalRequests[0];
    if (!request) throw new Error('承認要求が作られていません');
    return request;
  }

  it('案件・資料・根拠・成果物・実行・監査を往復できる', async () => {
    await runGreenCase();

    const record = await app.store.getCase(caseId);
    expect(record?.state).toBe('pass');
    expect(record?.permitted_operations).toEqual(['internal_draft.save']);
    expect(record?.actor_roles).toEqual(['ai_ops', 'process_owner']);

    const sources = await app.store.listSources(caseId);
    expect(sources).toHaveLength(1);
    expect(sources[0]?.allowed_roles.length).toBeGreaterThan(0);

    const artifacts = await app.store.listArtifacts(caseId);
    expect(artifacts.map((a) => a.kind).sort()).toEqual(
      ['case_brief', 'evidence_bundle', 'qa_result', 'work_draft'].sort(),
    );

    const jobs = await app.store.listExecutionJobs(caseId);
    expect(jobs.map((j) => j.operation)).toEqual(['internal_draft.save']);
    expect(jobs[0]?.rollback_ref).toBeTruthy();

    const audit = await app.store.listAuditEvents(caseId);
    expect(audit.length).toBeGreaterThan(5);
    const times = audit.map((e) => new Date(e.occurred_at).getTime());
    expect([...times].sort((a, b) => a - b)).toEqual(times);
  });

  it('evidence_bundle の claim は claims テーブルへも展開される', async () => {
    await runGreenCase();
    const client = new Client({ connectionString: DATABASE_URL });
    await client.connect();
    try {
      const { rows } = await client.query<{ count: string }>(
        'SELECT count(*)::text AS count FROM claims WHERE case_id = $1',
        [caseId],
      );
      expect(Number(rows[0]?.count ?? 0)).toBeGreaterThan(0);
    } finally {
      await client.end();
    }
  });

  it('承認の確保は 1 度しか成功しない(FR-033)', async () => {
    const request = await runApprovalCase();
    const args = {
      requestId: request.request_id,
      expectedStatus: 'pending' as const,
      cardVersion: request.packet.card_version,
      nonce: request.packet.nonce,
    };

    const first = await app.store.claimApprovalRequest(args);
    const second = await app.store.claimApprovalRequest(args);
    expect(first).not.toBeNull();
    expect(second).toBeNull();
  });

  it('古いカード版数・誤った nonce では確保できない', async () => {
    const request = await runApprovalCase();

    expect(
      await app.store.claimApprovalRequest({
        requestId: request.request_id,
        expectedStatus: 'pending',
        cardVersion: request.packet.card_version + 1,
        nonce: request.packet.nonce,
      }),
    ).toBeNull();

    expect(
      await app.store.claimApprovalRequest({
        requestId: request.request_id,
        expectedStatus: 'pending',
        cardVersion: request.packet.card_version,
        nonce: 'wrong-nonce',
      }),
    ).toBeNull();
  });

  it('同じ冪等性キーの実行は 2 行目を作れない(FR-041)', async () => {
    await runGreenCase();
    const jobs = await app.store.listExecutionJobs(caseId);
    const existing = jobs[0]!;

    await expect(
      app.store.insertExecutionJob({ ...existing, execution_id: `${existing.execution_id}_dup` }),
    ).rejects.toThrow();
  });

  it('承認からの再開が同一トランザクションで完了する', async () => {
    const request = await runApprovalCase();

    const outcome = await app.approvals.submitDecision({
      requestId: request.request_id,
      platformUserId: 'U_APPROVER',
      cardVersion: request.packet.card_version,
      nonce: request.packet.nonce,
      decision: {
        decision: 'approved',
        reason: '確認した',
        conditions: [],
        scope_override: null,
      },
    });

    expect(outcome.ok).toBe(true);
    const decisions = await app.store.listApprovalDecisions(caseId);
    expect(decisions).toHaveLength(1);

    const jobs = await app.store.listExecutionJobs(caseId);
    expect(jobs.map((j) => j.operation).sort()).toEqual([
      'external_email.send',
      'internal_draft.save',
    ]);
    expect(jobs.find((j) => j.operation === 'external_email.send')?.status).toBe(
      'handed_off_to_human',
    );

    const record = await app.store.getCase(caseId);
    expect(record?.state).toBe('pass');
    expect(record?.stage).toBe('closed');
  });

  it('トランザクション内の例外はすべて巻き戻る', async () => {
    await runGreenCase();
    const before = (await app.store.listAuditEvents(caseId)).length;

    await expect(
      app.store.transaction(async (tx) => {
        await tx.insertAuditEvent({
          event_id: `evt_rollback_${caseId}`,
          case_id: caseId,
          event_type: 'agent.run',
          actor: 'test',
          actor_role: 'system',
          occurred_at: new Date().toISOString(),
          input_refs: [],
          output_refs: [],
          decision: null,
          approval_request_id: null,
          execution_id: null,
          detail: {},
        });
        throw new Error('意図的な失敗');
      }),
    ).rejects.toThrow('意図的な失敗');

    expect((await app.store.listAuditEvents(caseId)).length).toBe(before);
  });
});
