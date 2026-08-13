/**
 * 承認パケットの生成(FR-023)。
 *
 * 行為・対象・プレビュー・根拠・影響・制約・ロールバック・承認者・期限・
 * 冪等性キーをすべて備えたものだけが実行キューへ進める。
 * 必須項目が 1 つでも欠ければ `validateApprovalPacket` が弾く。
 */

import { createHash } from 'node:crypto';
import {
  approvalPacketSchema,
  validateApprovalPacket,
  type ApprovalPacket,
  type EvidenceBundle,
  type QaResult,
  type WorkDraft,
} from '../domain/schemas.js';
import type { CaseRecord } from '../domain/types.js';
import { operationSpec, type OperationId } from '../domain/risk.js';
import { previewExcerpt } from '../security/redact.js';
import type { IdGenerator } from '../domain/ids.js';
import type { Clock } from '../domain/clock.js';

export interface PacketBuildInput {
  caseRecord: CaseRecord;
  draft: WorkDraft;
  evidence: EvidenceBundle;
  qa: QaResult;
  operation: OperationId;
  /** 既存カードを作り直す場合の版数。省略時は 1。 */
  cardVersion?: number;
}

export interface PacketBuilderOptions {
  /** 承認期限。手順書の Level 2(24 時間以内)に合わせる。 */
  ttlHours?: number;
  /** 根拠としてカードに載せる件数の上限。 */
  maxEvidence?: number;
}

export class ApprovalPacketBuilder {
  private readonly ttlHours: number;
  private readonly maxEvidence: number;

  constructor(
    private readonly ids: IdGenerator,
    private readonly clock: Clock,
    options: PacketBuilderOptions = {},
  ) {
    this.ttlHours = options.ttlHours ?? 24;
    this.maxEvidence = options.maxEvidence ?? 5;
  }

  build(input: PacketBuildInput): { ok: true; packet: ApprovalPacket } | { ok: false; missing: string[] } {
    const spec = operationSpec(input.operation);
    const candidate = input.draft.execution_candidates.find(
      (c) => c.operation === input.operation,
    );
    const target = candidate?.target ?? `case:${input.caseRecord.case_id}`;
    const recipients =
      input.operation === 'external_email.send'
        ? (input.draft.email_draft?.to ?? [])
        : [];

    const preview = this.buildPreview(input, target);
    const expiresAt = new Date(
      this.clock.now().getTime() + this.ttlHours * 60 * 60 * 1000,
    ).toISOString();

    const unresolved = input.qa.findings
      .filter((f) => f.category !== 'approval')
      .map((f) => `未解消の指摘: ${f.detail}`);

    const draftCandidate = {
      request_id: this.ids.next('req'),
      case_id: input.caseRecord.case_id,
      operation: input.operation,
      target,
      preview,
      evidence: input.evidence.claims.slice(0, this.maxEvidence).map((claim) => ({
        claim_id: claim.claim_id,
        summary: previewExcerpt(claim.statement, 120, input.caseRecord.permitted_personal_data),
      })),
      impact: this.buildImpact(input, spec.risk, recipients),
      constraints: [
        `許可される操作は ${input.operation} のみ`,
        `対象は ${target} のみ`,
        recipients.length > 0 ? `宛先は ${recipients.join(', ')} のみ` : '宛先の追加は許可しない',
        `根拠付与率 ${(input.qa.evidence_coverage * 100).toFixed(1)}%(未達分は承認者が確認する)`,
        ...unresolved,
      ],
      rollback: spec.rollback,
      required_role: 'approver',
      expires_at: expiresAt,
      idempotency_key: this.idempotencyKey(input, target),
      risk: spec.risk,
      granted_scope: { operation: input.operation, target, recipients },
      card_version: input.cardVersion ?? 1,
      nonce: this.ids.next('nonce'),
    };

    const validated = validateApprovalPacket(draftCandidate);
    if (!validated.ok) return validated;
    return { ok: true, packet: approvalPacketSchema.parse(validated.packet) };
  }

  /**
   * 冪等性キー(FR-041)。
   * 案件・操作・対象・実行内容が同じであれば同じキーになり、二重実行されない。
   */
  private idempotencyKey(input: PacketBuildInput, target: string): string {
    const material = JSON.stringify({
      case_id: input.caseRecord.case_id,
      operation: input.operation,
      target,
      document: input.draft.document,
      email: input.draft.email_draft,
    });
    return `idem_${createHash('sha256').update(material).digest('hex').slice(0, 32)}`;
  }

  private buildPreview(input: PacketBuildInput, target: string): string {
    const permitted = input.caseRecord.permitted_personal_data;
    if (input.operation === 'external_email.send' && input.draft.email_draft) {
      const email = input.draft.email_draft;
      return [
        `宛先: ${email.to.join(', ') || '(未設定)'}`,
        `件名: ${email.subject}`,
        `本文(抜粋): ${previewExcerpt(email.body, 280, permitted)}`,
      ].join('\n');
    }
    return [
      `対象: ${target}`,
      `表題: ${input.draft.document.title}`,
      `事実行: ${input.draft.document.fact_lines.length} 行 / タスク候補: ${input.draft.task_candidates.length} 件`,
      `抜粋: ${previewExcerpt(
        input.draft.document.fact_lines.map((l) => l.text).join(' '),
        280,
        permitted,
      )}`,
    ].join('\n');
  }

  private buildImpact(
    input: PacketBuildInput,
    risk: string,
    recipients: readonly string[],
  ): string {
    const spec = operationSpec(input.operation);
    const parts = [
      `リスク区分: ${risk.toUpperCase()}`,
      spec.reversible ? '可逆な操作' : '不可逆な操作',
    ];
    if (recipients.length > 0) parts.push(`社外 ${recipients.length} 件へ到達する`);
    if (!spec.autoExecutableInMvp) {
      parts.push('MVP では自動実行しない。承認後も人間が実行する');
    }
    return parts.join(' / ');
  }
}
