/**
 * 永続化する実体(要件定義 §7 データ要件)。
 *
 * すべての実体は `case_id` で連結され、監査(FR-042)から時系列で再現できる。
 */

import type { CaseState, StageId, ActorRole } from './states.js';
import type { OperationId, RiskTier } from './risk.js';
import type {
  ApprovalPacket,
  CaseBrief,
  EvidenceBundle,
  QaResult,
  WorkDraft,
  ExceptionCategory,
} from './schemas.js';

/** 資料の分類。データ責任者が設定する(FR-002)。 */
export type SourceClassification = 'public' | 'internal' | 'confidential' | 'restricted';

/** source_manifest の 1 行。 */
export interface SourceDocument {
  source_id: string;
  case_id: string;
  title: string;
  /** 原資料の本文。MVP は手動アップロードまたは限定フォルダのみ。 */
  content: string;
  classification: SourceClassification;
  updated_at: string;
  /** この資料を読める役割。ここに無い役割では参照できない(FR-002)。 */
  allowed_roles: readonly ActorRole[];
  /** 保持方針の識別子。 */
  retention_policy: string;
  /** 保持期限。過ぎた資料はエージェントへ渡さない。 */
  retention_expires_at: string | null;
}

/** 案件の正本(FR-001)。 */
export interface CaseRecord {
  case_id: string;
  objective: string | null;
  due_date: string | null;
  /** 希望成果物。 */
  desired_artifacts: readonly string[];
  target_workflow: string | null;
  business_owner: string | null;
  approver: string | null;
  /** 依頼者が許可した操作。ここに無い操作は候補にしない。 */
  permitted_operations: readonly OperationId[];
  /**
   * 目的上必要と宣言された個人情報の識別子(例: 送信先メールアドレス)。
   * ここに宣言されていない個人情報が成果物へ混入した場合は blocked_security。
   */
  permitted_personal_data: readonly string[];
  /** 案件を処理する主体のロール。資料アクセス判定に使う。 */
  actor_roles: readonly ActorRole[];
  state: CaseState;
  stage: StageId;
  risk: RiskTier;
  created_at: string;
  updated_at: string;
}

/** エージェント 1 回の実行証跡。 */
export interface AgentRun {
  run_id: string;
  case_id: string;
  role: 'supervisor' | 'knowledge' | 'improvement' | 'qa';
  /** 入力のハッシュ。同一入力の再実行を識別する。 */
  input_hash: string;
  output_schema_version: string;
  state: CaseState;
  error: string | null;
  started_at: string;
  finished_at: string;
}

export type ArtifactKind = 'case_brief' | 'evidence_bundle' | 'work_draft' | 'qa_result';

export interface ArtifactRecord {
  artifact_id: string;
  case_id: string;
  kind: ArtifactKind;
  version: number;
  payload: CaseBrief | EvidenceBundle | WorkDraft | QaResult;
  created_at: string;
}

export type ApprovalRequestStatus =
  | 'pending'
  | 'approved'
  | 'approved_with_conditions'
  | 'returned'
  | 'rejected'
  | 'expired';

/** HITL 要求の正本(FR-023)。 */
export interface ApprovalRequestRecord {
  request_id: string;
  case_id: string;
  packet: ApprovalPacket;
  status: ApprovalRequestStatus;
  /** 通知先チャットのメッセージ ID。カード更新に使う(FR-033)。 */
  chat_message_id: string | null;
  /** 消費済みの nonce。二重操作を拒否する。 */
  nonce_consumed: boolean;
  created_at: string;
  updated_at: string;
}

/** 承認の監査証跡(FR-042)。 */
export interface ApprovalDecisionRecord {
  decision_id: string;
  request_id: string;
  case_id: string;
  decision: 'approved' | 'approved_with_conditions' | 'returned' | 'rejected';
  reason: string;
  conditions: readonly string[];
  decided_by: string;
  decided_by_role: ActorRole;
  decided_at: string;
  /** 実際に許可された scope。承認条件で元の scope を拡張していないことが検証済み。 */
  granted_scope: {
    operation: OperationId;
    target: string;
    recipients: readonly string[];
  };
}

export type ExecutionStatus =
  | 'succeeded'
  | 'failed'
  | 'skipped_duplicate'
  | 'handed_off_to_human';

/** 限定実行の追跡(FR-041)。 */
export interface ExecutionJobRecord {
  execution_id: string;
  case_id: string;
  operation: OperationId;
  target: string;
  idempotency_key: string;
  status: ExecutionStatus;
  result: string;
  /** ロールバック参照。 */
  rollback_ref: string | null;
  approval_request_id: string | null;
  attempt: number;
  error: string | null;
  executed_at: string;
}

export type AuditEventType =
  | 'case.created'
  | 'case.state_changed'
  | 'agent.run'
  | 'artifact.created'
  | 'source.access_denied'
  | 'security.exception'
  | 'approval.requested'
  | 'approval.notified'
  | 'approval.action_rejected'
  | 'approval.decided'
  | 'execution.attempted'
  | 'execution.completed'
  | 'retry.limit_reached'
  | 'incident.declared';

/** 横断監査・KPI 集計の元データ(FR-042)。 */
export interface AuditEvent {
  event_id: string;
  case_id: string;
  event_type: AuditEventType;
  /** 主体。人間なら利用者 ID、システムならエージェント役割。 */
  actor: string;
  actor_role: ActorRole;
  occurred_at: string;
  /** 入力参照(source_id / artifact_id など)。 */
  input_refs: readonly string[];
  /** 出力参照。 */
  output_refs: readonly string[];
  /** 判断内容。 */
  decision: string | null;
  approval_request_id: string | null;
  execution_id: string | null;
  /** 補足。秘密情報・不要な個人情報を入れない(非機能要件)。 */
  detail: Record<string, unknown>;
}

/** FR-022 の再試行カウンタ。 */
export interface RetryCounterRecord {
  case_id: string;
  category: ExceptionCategory;
  root_cause: string;
  /** これまでに実施した自動差戻しの回数。 */
  auto_revisions: number;
}
