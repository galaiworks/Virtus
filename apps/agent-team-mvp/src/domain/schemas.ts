/**
 * エージェント共通の出力契約(手順書 C-1)。
 *
 * 各エージェントの出力は自由文ではなく JSON Schema(Zod)で検証する。
 * 全成果物は `status` / `facts` / `uncertainties` / `log_refs` / `next_action` を共通に持つ。
 */

import { z } from 'zod';
import { CASE_STATES } from './states.js';

/** 共通ヘッダ。すべてのエージェント成果物が持つ。 */
export const agentEnvelopeSchema = z.object({
  status: z.enum(CASE_STATES),
  /** 根拠 ID を伴う確定事実。 */
  facts: z.array(
    z.object({
      text: z.string().min(1),
      claim_ids: z.array(z.string()).default([]),
    }),
  ),
  /** 未確認事項。推測で埋めてはならない項目。 */
  uncertainties: z.array(z.string()).default([]),
  /** 監査ログ・実行証跡への参照。 */
  log_refs: z.array(z.string()).default([]),
  /** 次工程の指示。 */
  next_action: z.string().min(1),
});

export const riskTierSchema = z.enum(['green', 'yellow', 'red']);

export const operationIdSchema = z.enum([
  'internal_draft.save',
  'task_draft.create',
  'approval_request.post',
  'external_email.send',
  'crm.record.commit',
  'storage.delete',
  'storage.overwrite',
  'contract.sign',
  'pricing.commit',
  'spend.commit',
  'hr.decision',
]);

/** 例外カテゴリ。FR-022 の再試行上限はこのカテゴリ+根本原因で数える。 */
export const exceptionCategorySchema = z.enum([
  'security',
  'authorization',
  'fact_conflict',
  'approval',
  'clarification',
  'revision',
  'execution',
]);
export type ExceptionCategory = z.infer<typeof exceptionCategorySchema>;

/* ------------------------------------------------------------------ */
/* FR-010 統括エージェント: case_brief                                  */
/* ------------------------------------------------------------------ */

export const caseBriefSchema = agentEnvelopeSchema.extend({
  case_id: z.string().min(1),
  objective: z.string().min(1),
  kpi: z.array(z.string()).min(1),
  in_scope: z.array(z.string()),
  out_of_scope: z.array(z.string()),
  risks: z.array(
    z.object({
      description: z.string().min(1),
      tier: riskTierSchema,
    }),
  ),
  approver_role: z.string().min(1),
  stop_conditions: z.array(z.string()).min(1),
  open_questions: z.array(z.string()).default([]),
});
export type CaseBrief = z.infer<typeof caseBriefSchema>;

/* ------------------------------------------------------------------ */
/* FR-011 ナレッジ/データ: evidence_bundle                              */
/* ------------------------------------------------------------------ */

export const claimSchema = z.object({
  claim_id: z.string().min(1),
  statement: z.string().min(1),
  source_id: z.string().min(1),
  /** 該当箇所。原資料内の文字オフセットと引用。 */
  locator: z.object({
    start: z.number().int().nonnegative(),
    end: z.number().int().nonnegative(),
    quote: z.string().min(1),
  }),
  source_updated_at: z.string().min(1),
  confidence: z.number().min(0).max(1),
  /** 主張の種別。重要主張(数値・日付・決定事項)の判定に使う。 */
  kind: z.enum(['number', 'date', 'decision', 'statement']),
  /** 同一主題を指すキー。矛盾検出に使う。 */
  subject_key: z.string().min(1),
});
export type Claim = z.infer<typeof claimSchema>;

export const contradictionSchema = z.object({
  subject_key: z.string().min(1),
  claim_ids: z.array(z.string()).min(2),
  description: z.string().min(1),
});
export type Contradiction = z.infer<typeof contradictionSchema>;

export const evidenceBundleSchema = agentEnvelopeSchema.extend({
  case_id: z.string().min(1),
  claims: z.array(claimSchema),
  contradictions: z.array(contradictionSchema).default([]),
  /** 資料由来の限界。参照できなかった範囲など。 */
  limitations: z.array(z.string()).default([]),
  /** 権限外と判定して参照しなかった資料。 */
  denied_source_ids: z.array(z.string()).default([]),
});
export type EvidenceBundle = z.infer<typeof evidenceBundleSchema>;

/* ------------------------------------------------------------------ */
/* FR-012 業務改善: work_draft                                          */
/* ------------------------------------------------------------------ */

export const taskCandidateSchema = z.object({
  title: z.string().min(1),
  owner: z.string().min(1),
  due: z.string().nullable(),
  claim_ids: z.array(z.string()).default([]),
});

export const executionCandidateSchema = z.object({
  operation: operationIdSchema,
  target: z.string().min(1),
  /** 実行前に人間へ見せるプレビュー。 */
  preview: z.string().min(1),
  claim_ids: z.array(z.string()).default([]),
});
export type ExecutionCandidate = z.infer<typeof executionCandidateSchema>;

export const workDraftSchema = agentEnvelopeSchema.extend({
  case_id: z.string().min(1),
  /** 週報などの本文。事実・提案・未確認事項を分離して保持する。 */
  document: z.object({
    title: z.string().min(1),
    /** 根拠 ID 付きの事実行。 */
    fact_lines: z.array(
      z.object({
        text: z.string().min(1),
        claim_ids: z.array(z.string()),
      }),
    ),
    /** 提案。根拠に基づく解釈であり、事実と混ぜない。 */
    proposals: z.array(z.string()),
    /** 未確認事項。 */
    open_items: z.array(z.string()),
  }),
  task_candidates: z.array(taskCandidateSchema).default([]),
  execution_candidates: z.array(executionCandidateSchema).default([]),
  /** 顧客向けメール草案(任意)。 */
  email_draft: z
    .object({
      to: z.array(z.string()),
      subject: z.string().min(1),
      body: z.string().min(1),
    })
    .nullable()
    .default(null),
});
export type WorkDraft = z.infer<typeof workDraftSchema>;

/* ------------------------------------------------------------------ */
/* FR-013 品質/承認: qa_result                                          */
/* ------------------------------------------------------------------ */

export const qaFindingSchema = z.object({
  category: exceptionCategorySchema,
  /** 根本原因キー。FR-022 の再試行上限はこのキー単位で数える。 */
  root_cause: z.string().min(1),
  severity: z.enum(['blocker', 'major', 'minor']),
  detail: z.string().min(1),
  /** 指摘が指す対象(claim_id、fact_line index、operation など)。 */
  target: z.string().nullable().default(null),
});
export type QaFinding = z.infer<typeof qaFindingSchema>;

export const qaResultSchema = agentEnvelopeSchema.extend({
  case_id: z.string().min(1),
  findings: z.array(qaFindingSchema).default([]),
  /** 重要主張のうち根拠 ID が付いた割合(G2 / KPI 根拠付与率)。 */
  evidence_coverage: z.number().min(0).max(1),
  /** 人間介入が必要か。 */
  human_intervention_required: z.boolean(),
  /** 再開地点。 */
  resume_at: z.string().min(1),
  /** Green として即時実行してよい操作。 */
  permitted_operations: z.array(operationIdSchema).default([]),
  /** 承認が必要な操作。 */
  operations_requiring_approval: z.array(operationIdSchema).default([]),
});
export type QaResult = z.infer<typeof qaResultSchema>;

/* ------------------------------------------------------------------ */
/* FR-023 承認パケット                                                  */
/* ------------------------------------------------------------------ */

export const approvalPacketSchema = z.object({
  request_id: z.string().min(1),
  case_id: z.string().min(1),
  /** 行為 */
  operation: operationIdSchema,
  /** 対象 */
  target: z.string().min(1),
  /** プレビュー(宛先・件名・本文など、承認者が最終確認する内容) */
  preview: z.string().min(1),
  /** 根拠(claim_id と要約) */
  evidence: z.array(
    z.object({
      claim_id: z.string().min(1),
      summary: z.string().min(1),
    }),
  ),
  /** 影響 */
  impact: z.string().min(1),
  /** 制約(承認しても越えてはならない範囲) */
  constraints: z.array(z.string()).min(1),
  /** ロールバック方法 */
  rollback: z.string().min(1),
  /** 必要な承認ロール */
  required_role: z.string().min(1),
  /** 期限(ISO8601) */
  expires_at: z.string().min(1),
  /** 冪等性キー */
  idempotency_key: z.string().min(1),
  /** リスク区分 */
  risk: riskTierSchema,
  /** 承認された場合に許可される scope。承認条件でこれを拡張してはならない。 */
  granted_scope: z.object({
    operation: operationIdSchema,
    target: z.string().min(1),
    /** 対外行為の宛先。空配列は宛先なし。 */
    recipients: z.array(z.string()).default([]),
  }),
  /** カード版数。古いカードからの操作を拒否するために使う(FR-033)。 */
  card_version: z.number().int().positive(),
  /** ワンタイム値。 */
  nonce: z.string().min(1),
});
export type ApprovalPacket = z.infer<typeof approvalPacketSchema>;

/** FR-023: 必須項目が欠けた承認パケットは実行キューに入らない。 */
export function validateApprovalPacket(
  candidate: unknown,
): { ok: true; packet: ApprovalPacket } | { ok: false; missing: string[] } {
  const parsed = approvalPacketSchema.safeParse(candidate);
  if (parsed.success) return { ok: true, packet: parsed.data };
  const missing = parsed.error.issues.map((issue) => issue.path.join('.') || '(root)');
  return { ok: false, missing: [...new Set(missing)] };
}

export const approvalDecisionSchema = z.object({
  decision: z.enum(['approved', 'approved_with_conditions', 'returned', 'rejected']),
  reason: z.string().min(1),
  conditions: z.array(z.string()).default([]),
  /** 条件付き承認で絞り込まれた scope。元の granted_scope を拡張してはならない。 */
  scope_override: z
    .object({
      recipients: z.array(z.string()).optional(),
      target: z.string().optional(),
    })
    .nullable()
    .default(null),
});
export type ApprovalDecisionInput = z.infer<typeof approvalDecisionSchema>;
