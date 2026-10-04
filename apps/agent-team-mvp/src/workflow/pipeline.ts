/**
 * 固定順序のワークフロー(手順書 C-2)。
 *
 * 統括 → ナレッジ/データ → 業務改善 → 品質/承認 の順に固定する。
 * 並列化と自律的な再計画は、評価データで必要性が確認されるまで導入しない。
 *
 * | 順序 | 処理                         | 停止・分岐                          |
 * |-----:|------------------------------|-------------------------------------|
 * |    1 | 案件登録と必須項目確認       | 欠落時は needs_clarification        |
 * |    2 | 統括エージェントで案件化     | Red なら判断資料作成に限定          |
 * |    3 | ナレッジ/データで根拠作成    | 権限不備・古い資料・矛盾で停止      |
 * |    4 | 業務改善で下書き作成         | 根拠外の内容を追加しない            |
 * |    5 | 品質/承認で独立評価          | pass / 差戻し / 保留 / 承認待ち / 停止 |
 * |    6 | 許可済みの限定実行か人間介入 | Yellow/Red は承認後のみ             |
 * |    7 | 監査・KPI 記録               | 週次改善バックログへ送る            |
 */

import type { Store, StoreSession } from '../ports/store.js';
import type { IdGenerator } from '../domain/ids.js';
import type { Clock } from '../domain/clock.js';
import type { AuditRecorder } from '../audit/audit-log.js';
import type {
  AgentRun,
  ApprovalRequestRecord,
  ArtifactRecord,
  CaseRecord,
  ExecutionJobRecord,
  SourceDocument,
} from '../domain/types.js';
import type {
  CaseBrief,
  EvidenceBundle,
  QaFinding,
  QaResult,
  WorkDraft,
} from '../domain/schemas.js';
import type { CaseState, StageId } from '../domain/states.js';
import { allowsExecution, stateDefinition } from '../domain/states.js';
import { isGreenAutoExecutable, operationSpec, type OperationId } from '../domain/risk.js';
import type { SupervisorAgent } from '../agents/supervisor-agent.js';
import type { KnowledgeAgent } from '../agents/knowledge-agent.js';
import type { ImprovementAgent } from '../agents/improvement-agent.js';
import type { QaAgent } from '../agents/qa-agent.js';
import type { AgentResult } from '../agents/base-agent.js';
import { evaluateRetryBudget } from './retry-policy.js';
import type { ApprovalPacketBuilder } from '../approval/packet.js';
import type { ApprovalService } from '../approval/approval-service.js';
import type { ExecutionRunner } from '../execution/execution-runner.js';

export interface PipelineResult {
  caseId: string;
  state: CaseState;
  stage: StageId;
  brief: CaseBrief | null;
  evidence: EvidenceBundle | null;
  draft: WorkDraft | null;
  qa: QaResult | null;
  approvalRequests: ApprovalRequestRecord[];
  executions: ExecutionJobRecord[];
  /** 自動差戻しを行った回数。 */
  revisionRounds: number;
  findings: QaFinding[];
}

export interface OrchestratorDeps {
  store: Store;
  ids: IdGenerator;
  clock: Clock;
  audit: AuditRecorder;
  supervisor: SupervisorAgent;
  knowledge: KnowledgeAgent;
  improvement: ImprovementAgent;
  qa: QaAgent;
  packetBuilder: ApprovalPacketBuilder;
  approvals: ApprovalService;
  executor: ExecutionRunner;
}

/** 差戻しループの安全弁。FR-022 の上限に加えて絶対上限を置く。 */
const MAX_PIPELINE_ITERATIONS = 5;

export class Orchestrator {
  constructor(private readonly deps: OrchestratorDeps) {}

  /* ------------------------------------------------------------------ */
  /* 工程 1: 案件登録                                                     */
  /* ------------------------------------------------------------------ */

  async intake(input: {
    caseRecord: Omit<CaseRecord, 'state' | 'stage' | 'created_at' | 'updated_at' | 'risk'> &
      Partial<Pick<CaseRecord, 'risk'>>;
    sources: readonly Omit<SourceDocument, 'case_id'>[];
  }): Promise<CaseRecord> {
    const now = this.deps.clock.now().toISOString();
    const record: CaseRecord = {
      ...input.caseRecord,
      risk: input.caseRecord.risk ?? 'green',
      state: 'needs_clarification',
      stage: 'intake',
      created_at: now,
      updated_at: now,
    };

    return this.deps.store.transaction(async (tx) => {
      await tx.insertCase(record);
      for (const source of input.sources) {
        await tx.insertSource({ ...source, case_id: record.case_id });
      }
      await this.deps.audit.record(tx, {
        case_id: record.case_id,
        event_type: 'case.created',
        actor: record.business_owner ?? 'requester',
        actor_role: 'requester',
        input_refs: input.sources.map((s) => s.source_id),
        detail: {
          desired_artifacts: record.desired_artifacts,
          permitted_operations: record.permitted_operations,
        },
      });
      return record;
    });
  }

  /* ------------------------------------------------------------------ */
  /* 工程 2-7: 固定順序の実行                                             */
  /* ------------------------------------------------------------------ */

  async run(caseId: string): Promise<PipelineResult> {
    const caseRecord = await this.deps.store.getCase(caseId);
    if (!caseRecord) throw new Error(`案件が見つかりません: ${caseId}`);
    const sources = await this.deps.store.listSources(caseId);

    const result: PipelineResult = {
      caseId,
      state: 'needs_clarification',
      stage: 'intake',
      brief: null,
      evidence: null,
      draft: null,
      qa: null,
      approvalRequests: [],
      executions: [],
      revisionRounds: 0,
      findings: [],
    };

    /* 工程 2: 統括 */
    const supervisorRun = await this.deps.supervisor.execute({ caseRecord, sources });
    await this.persistRun(caseRecord, supervisorRun, 'case_brief');
    if (supervisorRun.state !== 'pass' || !supervisorRun.output) {
      return this.halt(result, caseRecord, supervisorRun.state, 'supervisor', supervisorRun.findings);
    }
    result.brief = supervisorRun.output;

    /* 工程 3: ナレッジ/データ */
    const knowledgeRun = await this.deps.knowledge.execute({ caseRecord, sources });
    await this.persistRun(caseRecord, knowledgeRun, 'evidence_bundle');
    result.evidence = knowledgeRun.output;
    if (knowledgeRun.state !== 'pass' || !knowledgeRun.output) {
      return this.halt(result, caseRecord, knowledgeRun.state, 'knowledge', knowledgeRun.findings);
    }
    const evidence = knowledgeRun.output;

    /* 工程 4-5: 業務改善 → 品質/承認(差戻しループ) */
    let revisionFeedback: string[] = [];
    let qaResult: QaResult | null = null;
    let draft: WorkDraft | null = null;

    for (let iteration = 0; iteration < MAX_PIPELINE_ITERATIONS; iteration += 1) {
      const improvementRun = await this.deps.improvement.execute({
        caseRecord,
        brief: result.brief,
        evidence,
        revisionFeedback,
      });
      await this.persistRun(caseRecord, improvementRun, 'work_draft');
      if (improvementRun.state !== 'pass' || !improvementRun.output) {
        return this.halt(
          result,
          caseRecord,
          improvementRun.state,
          'improvement',
          improvementRun.findings,
        );
      }
      draft = improvementRun.output;
      result.draft = draft;

      const qaRun = await this.deps.qa.execute({
        caseRecord,
        brief: result.brief,
        evidence,
        draft,
        upstreamFindings: [],
      });
      await this.persistRun(caseRecord, qaRun, 'qa_result');
      qaResult = qaRun.output;
      result.qa = qaResult;
      result.findings = qaRun.findings;

      if (qaRun.state !== 'needs_revision') break;

      /* FR-022: 同一カテゴリ・同一根本原因の自動差戻しは 2 回まで。 */
      const revisionFindings = qaRun.findings.filter((f) => f.category === 'revision');
      const budget = await this.deps.store.transaction((tx) =>
        evaluateRetryBudget(tx, caseId, revisionFindings),
      );

      if (!budget.allowAutoRevision) {
        await this.deps.store.transaction(async (tx) => {
          await this.deps.audit.record(tx, {
            case_id: caseId,
            event_type: 'retry.limit_reached',
            actor: 'orchestrator',
            actor_role: 'system',
            decision: 'human_review_required',
            detail: {
              category: budget.exhausted?.category ?? null,
              root_cause: budget.exhausted?.root_cause ?? null,
              auto_revisions: budget.exhausted?.auto_revisions ?? 0,
            },
          });
        });
        return this.halt(result, caseRecord, 'human_review_required', 'improvement', qaRun.findings);
      }

      result.revisionRounds += 1;
      revisionFeedback = revisionFindings.map((f) => f.detail);
    }

    if (!qaResult || !draft) {
      return this.halt(result, caseRecord, 'needs_revision', 'improvement', result.findings);
    }

    /* 工程 6: 承認または限定実行 */
    if (qaResult.status === 'awaiting_approval') {
      const requests = await this.createApprovalRequests(caseRecord, draft, evidence, qaResult);
      result.approvalRequests = requests;
      return this.halt(result, caseRecord, 'awaiting_approval', 'approval', qaResult.findings);
    }

    if (qaResult.status !== 'pass') {
      return this.halt(result, caseRecord, qaResult.status, stateDefinition(qaResult.status).resumeAt, qaResult.findings);
    }

    const executions = await this.deps.store.transaction((tx) =>
      this.executeGreenOperations(tx, caseRecord, draft, qaResult.permitted_operations),
    );
    result.executions = executions;

    const finalState: CaseState = executions.some((job) => job.status === 'failed')
      ? 'execution_failed'
      : 'pass';
    const finalStage: StageId = finalState === 'pass' ? 'closed' : 'execution';
    await this.setState(caseRecord, finalState, finalStage, 'pipeline_completed');

    result.state = finalState;
    result.stage = finalStage;
    return result;
  }

  /* ------------------------------------------------------------------ */
  /* 承認後の再開                                                         */
  /* ------------------------------------------------------------------ */

  /**
   * 承認済みの操作と、待たされていた Green 操作を実行する。
   * ApprovalService のトランザクション内から呼ばれる。
   */
  async resumeAfterApproval(
    tx: StoreSession,
    args: {
      caseRecord: CaseRecord;
      request: ApprovalRequestRecord;
      decision: { granted_scope: { operation: OperationId; target: string; recipients: readonly string[] } };
    },
  ): Promise<ExecutionJobRecord[]> {
    const { caseRecord, request, decision } = args;
    const draftArtifact = await tx.latestArtifact(caseRecord.case_id, 'work_draft');
    const draft = draftArtifact ? (draftArtifact.payload as WorkDraft) : null;
    const executions: ExecutionJobRecord[] = [];

    /* 承認された操作。scope は承認記録の granted_scope に限定する。 */
    const approvedOutcome = await this.deps.executor.run(tx, {
      caseRecord,
      operation: decision.granted_scope.operation,
      target: decision.granted_scope.target,
      payload: this.payloadFor(decision.granted_scope.operation, draft, decision.granted_scope.recipients),
      idempotencyKey: request.packet.idempotency_key,
      approvalRequestId: request.request_id,
      approvedScope: decision.granted_scope,
    });
    if (approvedOutcome.ok) executions.push(approvedOutcome.job);
    else if (approvedOutcome.refusal === 'execution_failed') executions.push(approvedOutcome.job);

    /* 他に未処理の承認要求が残っていれば、Green 操作はまだ動かさない。 */
    const pending = (await tx.listApprovalRequests(caseRecord.case_id)).filter(
      (r) => r.status === 'pending' && r.request_id !== request.request_id,
    );
    if (pending.length === 0 && draft) {
      const greens = draft.execution_candidates
        .map((c) => c.operation)
        .filter((op) => isGreenAutoExecutable(op));
      executions.push(...(await this.executeGreenOperations(tx, caseRecord, draft, greens)));
    }

    const failed = executions.some((job) => job.status === 'failed');
    const nextState: CaseState = failed ? 'execution_failed' : pending.length > 0 ? 'awaiting_approval' : 'pass';
    const nextStage: StageId = failed ? 'execution' : pending.length > 0 ? 'approval' : 'closed';
    await this.setStateWithin(tx, caseRecord, nextState, nextStage, 'approval_resumed');

    return executions;
  }

  /* ------------------------------------------------------------------ */
  /* 補助                                                                 */
  /* ------------------------------------------------------------------ */

  private async createApprovalRequests(
    caseRecord: CaseRecord,
    draft: WorkDraft,
    evidence: EvidenceBundle,
    qa: QaResult,
  ): Promise<ApprovalRequestRecord[]> {
    const requests: ApprovalRequestRecord[] = [];
    const evidenceSummary = evidence.claims.slice(0, 5).map((c) => c.statement);

    for (const operation of qa.operations_requiring_approval) {
      const built = this.deps.packetBuilder.build({
        caseRecord,
        draft,
        evidence,
        qa,
        operation,
      });
      if (!built.ok) {
        // FR-023: 必須項目が欠けた承認パケットは実行キューに入らない。
        await this.deps.store.transaction(async (tx) => {
          await this.deps.audit.record(tx, {
            case_id: caseRecord.case_id,
            event_type: 'approval.action_rejected',
            actor: 'orchestrator',
            actor_role: 'system',
            decision: 'packet_incomplete',
            detail: { operation, missing: built.missing },
          });
        });
        continue;
      }

      const record = await this.deps.store.transaction((tx) =>
        this.deps.approvals.requestApproval(tx, {
          caseRecord,
          packet: built.packet,
          evidenceSummary,
        }),
      );
      requests.push(record);
    }

    return requests;
  }

  private async executeGreenOperations(
    tx: StoreSession,
    caseRecord: CaseRecord,
    draft: WorkDraft,
    operations: readonly OperationId[],
  ): Promise<ExecutionJobRecord[]> {
    const executions: ExecutionJobRecord[] = [];
    for (const operation of [...new Set(operations)]) {
      if (!isGreenAutoExecutable(operation)) continue;
      const candidate = draft.execution_candidates.find((c) => c.operation === operation);
      const target = candidate?.target ?? `case:${caseRecord.case_id}`;
      const outcome = await this.deps.executor.run(tx, {
        caseRecord,
        operation,
        target,
        payload: this.payloadFor(operation, draft, []),
        idempotencyKey: this.greenIdempotencyKey(caseRecord, operation, target, draft),
      });
      if (outcome.ok) executions.push(outcome.job);
      else if (outcome.refusal === 'execution_failed') executions.push(outcome.job);
    }
    return executions;
  }

  private greenIdempotencyKey(
    caseRecord: CaseRecord,
    operation: OperationId,
    target: string,
    draft: WorkDraft,
  ): string {
    const signature = JSON.stringify({
      case_id: caseRecord.case_id,
      operation,
      target,
      document: draft.document,
      tasks: draft.task_candidates,
    });
    // 承認パケットと同じ材料で作れるよう、簡易なハッシュを使う。
    let hash = 0;
    for (let i = 0; i < signature.length; i += 1) {
      hash = (hash * 31 + signature.charCodeAt(i)) | 0;
    }
    return `idem_green_${operation}_${(hash >>> 0).toString(16)}`;
  }

  private payloadFor(
    operation: OperationId,
    draft: WorkDraft | null,
    recipients: readonly string[],
  ): Record<string, unknown> {
    if (!draft) return {};
    switch (operation) {
      case 'internal_draft.save':
        return { document: draft.document };
      case 'task_draft.create':
        return { tasks: draft.task_candidates };
      case 'external_email.send':
        return {
          to: [...recipients],
          subject: draft.email_draft?.subject ?? '',
          body: draft.email_draft?.body ?? '',
        };
      default:
        return { title: draft.document.title };
    }
  }

  private async persistRun<T>(
    caseRecord: CaseRecord,
    run: AgentResult<T>,
    kind: ArtifactRecord['kind'],
  ): Promise<void> {
    await this.deps.store.transaction(async (tx) => {
      const agentRun: AgentRun = {
        run_id: this.deps.ids.next('run'),
        case_id: caseRecord.case_id,
        role: run.role,
        input_hash: run.inputHash,
        output_schema_version: run.schemaVersion,
        state: run.state,
        error: run.error,
        started_at: run.startedAt,
        finished_at: run.finishedAt,
      };
      await tx.insertAgentRun(agentRun);

      const outputRefs: string[] = [];
      if (run.output) {
        const previous = await tx.latestArtifact(caseRecord.case_id, kind);
        const artifact: ArtifactRecord = {
          artifact_id: this.deps.ids.next('art'),
          case_id: caseRecord.case_id,
          kind,
          version: (previous?.version ?? 0) + 1,
          payload: run.output as unknown as ArtifactRecord['payload'],
          created_at: run.finishedAt,
        };
        await tx.insertArtifact(artifact);
        outputRefs.push(artifact.artifact_id);

        await this.deps.audit.record(tx, {
          case_id: caseRecord.case_id,
          event_type: 'artifact.created',
          actor: run.role,
          actor_role: 'system',
          output_refs: [artifact.artifact_id],
          detail: { kind, version: artifact.version },
        });
      }

      await this.deps.audit.record(tx, {
        case_id: caseRecord.case_id,
        event_type: 'agent.run',
        actor: run.role,
        actor_role: 'system',
        output_refs: outputRefs,
        decision: run.state,
        detail: {
          schema_version: run.schemaVersion,
          findings: run.findings.map((f) => ({ category: f.category, root_cause: f.root_cause })),
        },
      });

      for (const finding of run.findings.filter((f) => f.category === 'security')) {
        await this.deps.audit.record(tx, {
          case_id: caseRecord.case_id,
          event_type: 'security.exception',
          actor: run.role,
          actor_role: 'system',
          decision: 'blocked_security',
          detail: { root_cause: finding.root_cause, target: finding.target },
        });
      }

      for (const finding of run.findings.filter((f) => f.category === 'authorization')) {
        await this.deps.audit.record(tx, {
          case_id: caseRecord.case_id,
          event_type: 'source.access_denied',
          actor: run.role,
          actor_role: 'system',
          decision: 'blocked_authorization',
          detail: { root_cause: finding.root_cause, target: finding.target },
        });
      }
    });
  }

  private async halt(
    result: PipelineResult,
    caseRecord: CaseRecord,
    state: CaseState,
    stage: StageId,
    findings: readonly QaFinding[],
  ): Promise<PipelineResult> {
    await this.setState(caseRecord, state, stage, 'halted');
    result.state = state;
    result.stage = stage;
    if (findings.length > 0) result.findings = [...findings];
    return result;
  }

  private async setState(
    caseRecord: CaseRecord,
    state: CaseState,
    stage: StageId,
    reason: string,
  ): Promise<void> {
    await this.deps.store.transaction((tx) =>
      this.setStateWithin(tx, caseRecord, state, stage, reason),
    );
  }

  private async setStateWithin(
    tx: StoreSession,
    caseRecord: CaseRecord,
    state: CaseState,
    stage: StageId,
    reason: string,
  ): Promise<void> {
    const current = await tx.getCase(caseRecord.case_id);
    if (!current) return;
    const updated: CaseRecord = {
      ...current,
      state,
      stage,
      updated_at: this.deps.clock.now().toISOString(),
    };
    await tx.updateCase(updated);
    await this.deps.audit.record(tx, {
      case_id: caseRecord.case_id,
      event_type: 'case.state_changed',
      actor: 'orchestrator',
      actor_role: 'system',
      decision: state,
      detail: {
        from: current.state,
        to: state,
        stage,
        reason,
        execution_queue_open: allowsExecution(state),
        interveners: stateDefinition(state).interveners,
      },
    });
  }
}

/** 監査ログに残す操作ラベル。管理画面の表示に使う。 */
export function operationLabel(operation: OperationId): string {
  return operationSpec(operation).label;
}
