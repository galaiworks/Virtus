/**
 * 評価セットの実行(手順書 A-3 / E-1)。
 *
 * 判定するのは、出力文章の完全一致ではなく
 * 根拠・状態・権限・実行範囲・ログの有無。
 */

import { buildDeterministicApp } from '../app.js';
import { FixedClock } from '../domain/clock.js';
import { SequentialIdGenerator } from '../domain/ids.js';
import { EVAL_CASES, type EvalCase } from './cases.js';
import { EVAL_NOW } from './fixtures.js';
import type { OperationId } from '../domain/risk.js';
import type { CaseState } from '../domain/states.js';

export interface EvalCaseResult {
  id: string;
  group: EvalCase['group'];
  title: string;
  passed: boolean;
  failures: string[];
  observed: {
    state: CaseState;
    evidenceCoverage: number | null;
    revisionRounds: number;
    executedOperations: OperationId[];
    approvalRequests: number;
    auditEventTypes: string[];
  };
}

export interface EvalSuiteResult {
  total: number;
  passed: number;
  failed: number;
  results: EvalCaseResult[];
}

export async function runEvalCase(evalCase: EvalCase): Promise<EvalCaseResult> {
  const clock = new FixedClock(new Date(EVAL_NOW));
  const app = buildDeterministicApp({
    clock,
    ids: new SequentialIdGenerator(),
    ...(evalCase.makeLlm ? { llm: evalCase.makeLlm() } : {}),
  });

  try {
    await app.orchestrator.intake(evalCase.intake);
    const result = await app.orchestrator.run(evalCase.intake.caseRecord.case_id);

    const executions = await app.store.listExecutionJobs(evalCase.intake.caseRecord.case_id);
    const auditEvents = await app.store.listAuditEvents(evalCase.intake.caseRecord.case_id);
    const approvals = await app.store.listApprovalRequests(evalCase.intake.caseRecord.case_id);

    // 実際に「行われた」操作だけを数える。人間へ引き渡した分は実行に数えない。
    const executedOperations = executions
      .filter((job) => job.status === 'succeeded')
      .map((job) => job.operation);
    const auditEventTypes = [...new Set(auditEvents.map((e) => e.event_type))];

    const failures: string[] = [];
    const expect = evalCase.expect;

    if (result.state !== expect.state) {
      failures.push(`状態が期待と異なる: 期待 ${expect.state} / 実際 ${result.state}`);
    }

    if (expect.minEvidenceCoverage !== undefined) {
      const coverage = result.qa?.evidence_coverage ?? 0;
      if (coverage < expect.minEvidenceCoverage) {
        failures.push(
          `根拠付与率が不足: 期待 ${expect.minEvidenceCoverage} 以上 / 実際 ${coverage.toFixed(3)}`,
        );
      }
    }

    for (const operation of expect.forbiddenExecutedOperations ?? []) {
      if (executedOperations.includes(operation)) {
        failures.push(`実行されてはならない操作が実行された: ${operation}`);
      }
    }

    for (const operation of expect.expectedExecutedOperations ?? []) {
      if (!executedOperations.includes(operation)) {
        failures.push(`実行されるべき操作が実行されていない: ${operation}`);
      }
    }

    if (expect.expectApprovalRequest !== undefined) {
      const hasRequest = approvals.length > 0;
      if (hasRequest !== expect.expectApprovalRequest) {
        failures.push(
          `承認要求の有無が期待と異なる: 期待 ${expect.expectApprovalRequest} / 実際 ${hasRequest}`,
        );
      }
    }

    for (const eventType of expect.expectedAuditEvents ?? []) {
      if (!auditEventTypes.includes(eventType)) {
        failures.push(`監査ログに ${eventType} が残っていない`);
      }
    }

    if (
      expect.expectedRevisionRounds !== undefined &&
      result.revisionRounds !== expect.expectedRevisionRounds
    ) {
      failures.push(
        `自動差戻し回数が期待と異なる: 期待 ${expect.expectedRevisionRounds} / 実際 ${result.revisionRounds}`,
      );
    }

    // 全ケース共通: case_id から状態遷移を時系列で再現できること(FR-042)。
    if (auditEvents.length === 0) {
      failures.push('監査イベントが 1 件も記録されていない');
    }

    return {
      id: evalCase.id,
      group: evalCase.group,
      title: evalCase.title,
      passed: failures.length === 0,
      failures,
      observed: {
        state: result.state,
        evidenceCoverage: result.qa?.evidence_coverage ?? null,
        revisionRounds: result.revisionRounds,
        executedOperations,
        approvalRequests: approvals.length,
        auditEventTypes,
      },
    };
  } finally {
    await app.close();
  }
}

export async function runEvalSuite(cases: readonly EvalCase[] = EVAL_CASES): Promise<EvalSuiteResult> {
  const results: EvalCaseResult[] = [];
  for (const evalCase of cases) {
    results.push(await runEvalCase(evalCase));
  }
  const passed = results.filter((r) => r.passed).length;
  return { total: results.length, passed, failed: results.length - passed, results };
}
