/**
 * 管理 API(FR-043)。
 *
 * 案件一覧、状態、根拠、下書き、承認履歴、例外、実行履歴を返す。
 * 業務オーナーと AI 運用担当が「停止理由」と「再開条件」を確認できることが要件。
 */

import type { FastifyInstance } from 'fastify';
import type { App } from '../app.js';
import { stateDefinition, type CaseState } from '../domain/states.js';
import type { CaseRecord } from '../domain/types.js';
import type { QaResult, WorkDraft, EvidenceBundle, CaseBrief } from '../domain/schemas.js';

export function registerAdminRoutes(server: FastifyInstance, app: App): void {
  server.get('/api/health', async () => ({
    ok: true,
    chat: app.chat.name,
    llm: app.llm.name,
    store: app.config.store,
  }));

  /* 案件一覧。停止理由と再開条件を一覧で見せる。 */
  server.get('/api/cases', async () => {
    const cases = await app.store.listCases();
    return { cases: cases.map(summarize) };
  });

  /* 案件詳細。case_id から根拠・下書き・承認・実行・監査をすべてたどれる(FR-003 / FR-042)。 */
  server.get<{ Params: { caseId: string } }>('/api/cases/:caseId', async (request, reply) => {
    const caseRecord = await app.store.getCase(request.params.caseId);
    if (!caseRecord) return reply.code(404).send({ error: 'case not found' });

    const [sources, runs, artifacts, approvals, decisions, executions, audit, retries] =
      await Promise.all([
        app.store.listSources(caseRecord.case_id),
        app.store.listAgentRuns(caseRecord.case_id),
        app.store.listArtifacts(caseRecord.case_id),
        app.store.listApprovalRequests(caseRecord.case_id),
        app.store.listApprovalDecisions(caseRecord.case_id),
        app.store.listExecutionJobs(caseRecord.case_id),
        app.store.listAuditEvents(caseRecord.case_id),
        app.store.listRetryCounters(caseRecord.case_id),
      ]);

    const latest = <T>(kind: string): T | null => {
      const matching = artifacts.filter((a) => a.kind === kind).sort((a, b) => a.version - b.version);
      const last = matching.at(-1);
      return last ? (last.payload as T) : null;
    };

    const qa = latest<QaResult>('qa_result');

    return {
      case: summarize(caseRecord),
      /* 資料は本文を返さない。分類・更新日・アクセスロールだけを見せる。 */
      sources: sources.map((s) => ({
        source_id: s.source_id,
        title: s.title,
        classification: s.classification,
        updated_at: s.updated_at,
        allowed_roles: s.allowed_roles,
        retention_policy: s.retention_policy,
        retention_expires_at: s.retention_expires_at,
      })),
      brief: latest<CaseBrief>('case_brief'),
      evidence: latest<EvidenceBundle>('evidence_bundle'),
      draft: latest<WorkDraft>('work_draft'),
      qa,
      agent_runs: runs,
      approvals: approvals.map((a) => ({
        request_id: a.request_id,
        status: a.status,
        operation: a.packet.operation,
        risk: a.packet.risk,
        expires_at: a.packet.expires_at,
        card_version: a.packet.card_version,
        constraints: a.packet.constraints,
        rollback: a.packet.rollback,
      })),
      approval_decisions: decisions,
      executions,
      /* 例外の一覧。停止理由の一次情報。 */
      exceptions: qa?.findings ?? [],
      retry_counters: retries,
      audit_events: audit,
      evaluation: {
        evidence_coverage: qa?.evidence_coverage ?? null,
        human_intervention_required: qa?.human_intervention_required ?? null,
      },
    };
  });

  server.get<{ Params: { caseId: string } }>('/api/cases/:caseId/audit', async (request, reply) => {
    const caseRecord = await app.store.getCase(request.params.caseId);
    if (!caseRecord) return reply.code(404).send({ error: 'case not found' });
    return { audit_events: await app.store.listAuditEvents(caseRecord.case_id) };
  });

  /* 案件登録(FR-001)。必須項目が欠ければパイプラインが needs_clarification で止める。 */
  server.post<{ Body: { case: Record<string, unknown>; sources?: unknown[] } }>(
    '/api/cases',
    async (request, reply) => {
      const body = request.body;
      if (!body?.case || typeof body.case !== 'object') {
        return reply.code(400).send({ error: 'case is required' });
      }
      const created = await app.orchestrator.intake({
        caseRecord: body.case as never,
        sources: (body.sources ?? []) as never,
      });
      return reply.code(201).send({ case_id: created.case_id });
    },
  );

  server.post<{ Params: { caseId: string } }>('/api/cases/:caseId/run', async (request, reply) => {
    const caseRecord = await app.store.getCase(request.params.caseId);
    if (!caseRecord) return reply.code(404).send({ error: 'case not found' });
    const result = await app.orchestrator.run(caseRecord.case_id);
    return {
      case_id: result.caseId,
      state: result.state,
      stage: result.stage,
      revision_rounds: result.revisionRounds,
      evidence_coverage: result.qa?.evidence_coverage ?? null,
      approval_requests: result.approvalRequests.map((r) => r.request_id),
      executions: result.executions.map((e) => ({
        execution_id: e.execution_id,
        operation: e.operation,
        status: e.status,
      })),
      findings: result.findings,
      resume: describeState(result.state),
    };
  });
}

function summarize(record: CaseRecord) {
  return {
    case_id: record.case_id,
    objective: record.objective,
    due_date: record.due_date,
    business_owner: record.business_owner,
    approver: record.approver,
    state: record.state,
    stage: record.stage,
    risk: record.risk,
    desired_artifacts: record.desired_artifacts,
    permitted_operations: record.permitted_operations,
    created_at: record.created_at,
    updated_at: record.updated_at,
    ...describeState(record.state),
  };
}

/** 停止理由と再開条件。管理画面が必ず表示する項目。 */
function describeState(state: CaseState) {
  const def = stateDefinition(state);
  return {
    system_action: def.systemAction,
    interveners: def.interveners,
    execution_queue_halted: def.halts.executionQueue,
    agent_pipeline_halted: def.halts.agentPipeline,
    resume_at: def.resumeAt,
    requires_explicit_human_restart: def.incident,
  };
}
