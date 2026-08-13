/**
 * エージェント統合(手順書 E-1)。
 *
 * 正常系、入力不足、根拠矛盾、権限逸脱、外部メール草案を、
 * プロンプト・モデル・ツール変更のたびに再実行する層。
 */

import { describe, expect, it } from 'vitest';
import { buildDeterministicApp } from '../../src/app.js';
import { FixedClock } from '../../src/domain/clock.js';
import { SequentialIdGenerator } from '../../src/domain/ids.js';
import { ScriptedLlmAdapter } from '../../src/adapters/llm/scripted-llm.js';
import { buildIntake, EVAL_NOW, MEETING_MINUTES, PLAN_CONFLICTING_DEADLINE } from '../../src/eval/fixtures.js';
import type { IntakeInput } from '../../src/eval/fixtures.js';
import type { LlmAdapter } from '../../src/ports/llm.js';

function makeApp(llm?: LlmAdapter) {
  return buildDeterministicApp({
    clock: new FixedClock(new Date(EVAL_NOW)),
    ids: new SequentialIdGenerator(),
    ...(llm ? { llm } : {}),
  });
}

async function runCase(intake: IntakeInput, llm?: LlmAdapter) {
  const app = makeApp(llm);
  await app.orchestrator.intake(intake);
  const result = await app.orchestrator.run(intake.caseRecord.case_id);
  return { app, result };
}

const minutes = (id: string) => ({
  source_id: `${id}_src`,
  title: '定例会議 議事録',
  content: MEETING_MINUTES,
});

describe('正常系', () => {
  it('週報下書きは事実・提案・未確認事項を分けて持ち、事実行はすべて根拠 ID を持つ', async () => {
    const { app, result } = await runCase(buildIntake({ case_id: 'case_a1' }, [minutes('case_a1')]));

    expect(result.state).toBe('pass');
    expect(result.draft).not.toBeNull();
    const draft = result.draft!;

    expect(draft.document.fact_lines.length).toBeGreaterThan(0);
    for (const line of draft.document.fact_lines) {
      expect(line.claim_ids.length).toBeGreaterThan(0);
    }
    expect(draft.document.proposals).toBeDefined();
    expect(draft.document.open_items).toBeDefined();
    expect(result.qa?.evidence_coverage).toBe(1);
    await app.close();
  });

  it('根拠は出典・該当箇所・更新日・信頼度を持つ(FR-011)', async () => {
    const { app, result } = await runCase(buildIntake({ case_id: 'case_a2' }, [minutes('case_a2')]));
    const claims = result.evidence?.claims ?? [];
    expect(claims.length).toBeGreaterThan(0);
    for (const claim of claims) {
      expect(claim.source_id).toBe('case_a2_src');
      expect(claim.locator.quote.length).toBeGreaterThan(0);
      expect(claim.locator.end).toBeGreaterThan(claim.locator.start);
      expect(claim.source_updated_at).toBeTruthy();
      expect(claim.confidence).toBeGreaterThan(0);
    }
    await app.close();
  });

  it('case_id から入力資料・下書き・実行結果をたどれる(FR-003 / FR-042)', async () => {
    const { app } = await runCase(buildIntake({ case_id: 'case_a3' }, [minutes('case_a3')]));

    const artifacts = await app.store.listArtifacts('case_a3');
    expect(artifacts.map((a) => a.kind).sort()).toEqual(
      ['case_brief', 'evidence_bundle', 'qa_result', 'work_draft'].sort(),
    );

    const audit = await app.store.listAuditEvents('case_a3');
    expect(audit.map((e) => e.event_type)).toContain('case.created');
    expect(audit.map((e) => e.event_type)).toContain('execution.completed');
    // 時系列で並んでいる。
    const times = audit.map((e) => new Date(e.occurred_at).getTime());
    expect([...times].sort((a, b) => a - b)).toEqual(times);
    await app.close();
  });
});

describe('入力不足', () => {
  it('目的・期限・承認者が無ければ needs_clarification で止まり、実行キューに入らない', async () => {
    const { app, result } = await runCase(
      buildIntake({ case_id: 'case_b1', objective: null, due_date: null, approver: null }, [
        minutes('case_b1'),
      ]),
    );

    expect(result.state).toBe('needs_clarification');
    expect(result.findings.map((f) => f.root_cause)).toEqual(
      expect.arrayContaining(['missing_field:objective', 'missing_field:due_date', 'missing_field:approver']),
    );
    expect(await app.store.listExecutionJobs('case_b1')).toHaveLength(0);
    await app.close();
  });
});

describe('根拠矛盾', () => {
  it('資料間で期限が異なれば hold_for_decision となり、選択肢を人間へ渡す', async () => {
    const { app, result } = await runCase(
      buildIntake({ case_id: 'case_c1' }, [
        minutes('case_c1'),
        { source_id: 'case_c1_plan', title: '計画書', content: PLAN_CONFLICTING_DEADLINE },
      ]),
    );

    expect(result.state).toBe('hold_for_decision');
    const contradictions = result.evidence?.contradictions ?? [];
    expect(contradictions.length).toBeGreaterThan(0);
    expect(contradictions[0]?.claim_ids.length).toBeGreaterThanOrEqual(2);
    expect(await app.store.listExecutionJobs('case_c1')).toHaveLength(0);
    await app.close();
  });
});

describe('権限逸脱', () => {
  it('アクセスロール外の資料は参照されず blocked_authorization になる', async () => {
    const { app, result } = await runCase(
      buildIntake({ case_id: 'case_d1' }, [
        minutes('case_d1'),
        {
          source_id: 'case_d1_hr',
          title: '人事評価記録',
          content: '人事評価記録。対象者 3 名の評価を記載する。',
          classification: 'restricted',
          allowed_roles: ['data_owner'],
        },
      ]),
    );

    expect(result.state).toBe('blocked_authorization');
    expect(result.evidence?.denied_source_ids).toContain('case_d1_hr');
    // 権限外資料からは根拠を作らない。
    expect(result.evidence?.claims.every((c) => c.source_id !== 'case_d1_hr')).toBe(true);

    const audit = await app.store.listAuditEvents('case_d1');
    expect(audit.map((e) => e.event_type)).toContain('source.access_denied');
    await app.close();
  });
});

describe('外部メール草案', () => {
  it('顧客メール送信は awaiting_approval となり、送信されない(G3)', async () => {
    const intake = buildIntake(
      {
        case_id: 'case_e1',
        desired_artifacts: ['weekly_report', 'email_draft'],
        permitted_operations: ['internal_draft.save', 'external_email.send'],
        permitted_personal_data: ['client@example.com'],
      },
      [minutes('case_e1')],
    );
    const { app, result } = await runCase(intake);

    expect(result.state).toBe('awaiting_approval');
    expect(result.approvalRequests).toHaveLength(1);
    expect(result.draft?.email_draft).not.toBeNull();

    const jobs = await app.store.listExecutionJobs('case_e1');
    expect(jobs).toHaveLength(0);

    const packet = result.approvalRequests[0]!.packet;
    expect(packet.risk).toBe('yellow');
    expect(packet.granted_scope.recipients).toEqual(['client@example.com']);
    expect(packet.rollback.length).toBeGreaterThan(0);
    expect(packet.idempotency_key).toMatch(/^idem_/);
    await app.close();
  });
});

describe('LLM の異常応答', () => {
  it('拒否は human_review_required として自動ループを止める', async () => {
    const llm = new ScriptedLlmAdapter({
      failures: [{ schemaName: 'improvement_prose', result: 'refusal', reason: 'テスト用の拒否' }],
    });
    const { app, result } = await runCase(buildIntake({ case_id: 'case_f1' }, [minutes('case_f1')]), llm);
    expect(result.state).toBe('human_review_required');
    expect(await app.store.listExecutionJobs('case_f1')).toHaveLength(0);
    await app.close();
  });

  it('打ち切りは出力契約違反として差戻し対象になる', async () => {
    const llm = new ScriptedLlmAdapter({
      failures: [{ schemaName: 'improvement_prose', result: 'incomplete', reason: 'max_tokens' }],
    });
    const { app, result } = await runCase(buildIntake({ case_id: 'case_f2' }, [minutes('case_f2')]), llm);
    expect(result.state).toBe('needs_revision');
    await app.close();
  });

  it('基盤障害は execution_failed として運用判断へ回す', async () => {
    const llm = new ScriptedLlmAdapter({
      failures: [{ schemaName: 'supervisor_prose', result: 'transport_error', reason: 'network' }],
    });
    const { app, result } = await runCase(buildIntake({ case_id: 'case_f3' }, [minutes('case_f3')]), llm);
    expect(result.state).toBe('execution_failed');
    await app.close();
  });
});

describe('根拠外の事実追加を防ぐ(FR-012)', () => {
  it('LLM が根拠に無い数値を書いた事実行は採用せず、原文の根拠へ差し替える', async () => {
    const llm = new ScriptedLlmAdapter({
      responders: {
        improvement_prose: (request) => {
          const ctx = request.context ?? {};
          const facts = Array.isArray(ctx.fact_line_texts) ? (ctx.fact_line_texts as string[]) : [];
          return {
            title: '週次報告(下書き)',
            // 1 行目だけ根拠に無い数値へ書き換える。
            fact_line_texts: facts.map((text, index) => (index === 0 ? '進捗率は 99% となった。' : text)),
            proposals: [],
            email: null,
          };
        },
      },
    });
    const { app, result } = await runCase(buildIntake({ case_id: 'case_g1' }, [minutes('case_g1')]), llm);

    const texts = result.draft?.document.fact_lines.map((l) => l.text) ?? [];
    expect(texts.some((t) => t.includes('99%'))).toBe(false);
    expect(result.qa?.evidence_coverage).toBe(1);
    expect(result.state).toBe('pass');
    await app.close();
  });
});
