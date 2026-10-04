/**
 * 日常の案件処理(手順書 F-2)を 1 件分たどるデモ。
 *
 *   npm run demo
 *
 * 外部通信を行わず、決定論アダプタで最初から最後まで実行する。
 * 承認待ちで止まり、承認したうえで限定実行されるところまでを見せる。
 */

import { buildDeterministicApp } from '../src/app.js';
import { FixedClock } from '../src/domain/clock.js';
import { SequentialIdGenerator } from '../src/domain/ids.js';
import { StaticIdentityResolver } from '../src/ports/identity.js';
import { MemoryChatAdapter } from '../src/adapters/chat/memory-chat.js';
import { buildIntake, EVAL_NOW, MEETING_MINUTES } from '../src/eval/fixtures.js';
import { stateDefinition } from '../src/domain/states.js';

const CASE_ID = 'case_demo';

async function main(): Promise<void> {
  const clock = new FixedClock(new Date(EVAL_NOW));
  const chat = new MemoryChatAdapter();
  const app = buildDeterministicApp({
    clock,
    chat,
    ids: new SequentialIdGenerator(),
    identities: new StaticIdentityResolver({
      U_APPROVER: { userId: 'approver-1', displayName: '承認権者', role: 'approver' },
    }),
  });

  /* 1. 依頼者が案件を登録する。 */
  const intake = buildIntake(
    {
      case_id: CASE_ID,
      objective: '会議録から社内週報とタスク候補、顧客向けメール草案を作る',
      desired_artifacts: ['weekly_report', 'task_candidates', 'email_draft'],
      permitted_operations: ['internal_draft.save', 'task_draft.create', 'external_email.send'],
      permitted_personal_data: ['client@example.com'],
    },
    [{ source_id: 'src_demo_min', title: '定例会議 議事録', content: MEETING_MINUTES }],
  );
  await app.orchestrator.intake(intake);
  console.log(`■ 1. 案件登録: ${CASE_ID}`);

  /* 2-5. 固定順序で 4 エージェントを回す。 */
  const result = await app.orchestrator.run(CASE_ID);
  const def = stateDefinition(result.state);

  console.log('\n■ 2-5. エージェント実行');
  console.log(`  状態          : ${result.state}`);
  console.log(`  システムの動作: ${def.systemAction}`);
  console.log(`  介入者        : ${def.interveners.join(', ') || '(不要)'}`);
  console.log(`  再開地点      : ${def.resumeAt}`);
  console.log(`  根拠付与率    : ${((result.qa?.evidence_coverage ?? 0) * 100).toFixed(1)}%`);
  console.log(`  根拠件数      : ${result.evidence?.claims.length ?? 0}`);

  console.log('\n  事実(根拠 ID 付き):');
  for (const line of result.draft?.document.fact_lines ?? []) {
    console.log(`    - ${line.text} [${line.claim_ids.join(', ')}]`);
  }
  console.log('  提案:');
  for (const proposal of result.draft?.document.proposals ?? []) {
    console.log(`    - ${proposal}`);
  }
  console.log('  未確認事項:');
  for (const item of result.draft?.document.open_items ?? []) {
    console.log(`    - ${item}`);
  }

  console.log('\n  指摘:');
  for (const finding of result.findings) {
    console.log(`    - [${finding.category}/${finding.severity}] ${finding.detail}`);
  }

  /* 6. 承認。 */
  const request = result.approvalRequests[0];
  if (!request) {
    console.log('\n■ 6. 承認は不要でした。');
  } else {
    console.log('\n■ 6. 承認カード(Slack へ送られる内容)');
    console.log(`  行為      : ${request.packet.operation}`);
    console.log(`  リスク    : ${request.packet.risk}`);
    console.log(`  期限      : ${request.packet.expires_at}`);
    console.log(`  対象      : ${request.packet.granted_scope.target}`);
    console.log(`  制約      : ${request.packet.constraints.join(' / ')}`);
    console.log(`  ロールバック: ${request.packet.rollback}`);
    console.log(`  プレビュー:\n${indent(request.packet.preview, 4)}`);

    const outcome = await app.approvals.submitDecision({
      requestId: request.request_id,
      platformUserId: 'U_APPROVER',
      cardVersion: request.packet.card_version,
      nonce: request.packet.nonce,
      decision: {
        decision: 'approved',
        reason: '宛先と本文を確認した',
        conditions: [],
        scope_override: null,
      },
    });
    console.log(`\n  承認結果  : ${outcome.ok ? '承認' : `拒否(${outcome.refusal})`}`);
  }

  /* 7. 監査。 */
  const executions = await app.store.listExecutionJobs(CASE_ID);
  console.log('\n■ 7. 実行結果');
  for (const job of executions) {
    console.log(`  - ${job.operation}: ${job.status} / ${job.result}`);
  }

  const audit = await app.store.listAuditEvents(CASE_ID);
  console.log(`\n■ 監査イベント(${audit.length} 件、case_id で時系列に再現可能)`);
  for (const event of audit) {
    console.log(`  ${event.occurred_at} ${event.event_type.padEnd(22)} ${event.decision ?? ''}`);
  }

  await app.close();
}

function indent(text: string, spaces: number): string {
  const pad = ' '.repeat(spaces);
  return text
    .split('\n')
    .map((line) => pad + line)
    .join('\n');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
