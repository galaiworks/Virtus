/**
 * HITL 承認サービス(FR-030〜FR-034、手順書 D-3)。
 *
 * カードは表示層である。カードが返す `approve` をそのまま実行してはならない。
 * 操作を受信したら、次の順序でサーバー側が再検証する。
 *
 * 1. プラットフォーム由来の正規リクエストか(HTTP 層で署名検証済み)
 * 2. 利用者 ID を内部の本人・ロールへ対応づける
 * 3. 案件の正本を読み、状態・期限・カード版数・nonce を確認する
 * 4. 承認者が必要ロールを満たすか確認する
 * 5. 承認条件が元の scope を拡張していないか確認する
 * 6. 決定を監査ログへ原子的に保存する
 * 7. 実行が許可された場合だけ、冪等性キー付きで限定実行する
 * 8. 元カード・スレッドを最終状態に更新する
 */

import type { Store, StoreSession } from '../ports/store.js';
import type { ChatAdapter, FinalCardState } from '../ports/chat.js';
import type { IdentityResolver, InternalIdentity } from '../ports/identity.js';
import type { AuditRecorder } from '../audit/audit-log.js';
import type { IdGenerator } from '../domain/ids.js';
import type { Clock } from '../domain/clock.js';
import type {
  ApprovalDecisionRecord,
  ApprovalRequestRecord,
  CaseRecord,
  ExecutionJobRecord,
} from '../domain/types.js';
import {
  approvalDecisionSchema,
  type ApprovalDecisionInput,
  type ApprovalPacket,
} from '../domain/schemas.js';
import { previewExcerpt } from '../security/redact.js';

export type ApprovalRefusal =
  | 'not_found'
  | 'unknown_identity'
  | 'forbidden_role'
  | 'expired'
  | 'already_processed'
  | 'stale_card'
  | 'invalid_decision'
  | 'scope_expansion'
  | 'case_not_found';

export type ApprovalOutcome =
  | {
      ok: true;
      request: ApprovalRequestRecord;
      decision: ApprovalDecisionRecord;
      executions: ExecutionJobRecord[];
    }
  | { ok: false; refusal: ApprovalRefusal; message: string };

export interface ApprovalDetails {
  packet: ApprovalPacket;
  status: ApprovalRequestRecord['status'];
  /** 最終確定画面に出す確認項目。 */
  finalConfirmation: {
    operation: string;
    target: string;
    recipients: readonly string[];
    previewExcerpt: string;
    constraints: readonly string[];
    rollback: string;
  };
}

/** 承認後に Green 操作を含めて再開するためのフック。 */
export type ResumeAfterApproval = (
  tx: StoreSession,
  args: {
    caseRecord: CaseRecord;
    request: ApprovalRequestRecord;
    decision: ApprovalDecisionRecord;
  },
) => Promise<ExecutionJobRecord[]>;

export interface ApprovalServiceDeps {
  store: Store;
  chat: ChatAdapter;
  identities: IdentityResolver;
  audit: AuditRecorder;
  ids: IdGenerator;
  clock: Clock;
  resumeAfterApproval: ResumeAfterApproval;
  /** 承認カードの送信先。DM または限定チャンネル。 */
  approvalChannel: string;
}

export class ApprovalService {
  constructor(private readonly deps: ApprovalServiceDeps) {}

  /**
   * 承認依頼を作成し、通知する(FR-023 / D-2 ステップ 1)。
   * 通知先はカード表示層であり、実行権限そのものは載せない。
   */
  async requestApproval(
    tx: StoreSession,
    args: { caseRecord: CaseRecord; packet: ApprovalPacket; evidenceSummary: readonly string[] },
  ): Promise<ApprovalRequestRecord> {
    const now = this.deps.clock.now().toISOString();
    const record: ApprovalRequestRecord = {
      request_id: args.packet.request_id,
      case_id: args.caseRecord.case_id,
      packet: args.packet,
      status: 'pending',
      chat_message_id: null,
      nonce_consumed: false,
      created_at: now,
      updated_at: now,
    };
    await tx.insertApprovalRequest(record);
    await this.deps.audit.record(tx, {
      case_id: args.caseRecord.case_id,
      event_type: 'approval.requested',
      actor: 'qa',
      actor_role: 'system',
      approval_request_id: record.request_id,
      decision: 'awaiting_approval',
      detail: {
        operation: args.packet.operation,
        risk: args.packet.risk,
        expires_at: args.packet.expires_at,
      },
    });

    const posted = await this.deps.chat.postApprovalRequest({
      packet: args.packet,
      channel: this.deps.approvalChannel,
      evidenceSummary: args.evidenceSummary,
    });

    const notified: ApprovalRequestRecord = {
      ...record,
      chat_message_id: posted.messageId,
      updated_at: this.deps.clock.now().toISOString(),
    };
    await tx.updateApprovalRequest(notified);
    await this.deps.audit.record(tx, {
      case_id: args.caseRecord.case_id,
      event_type: 'approval.notified',
      actor: this.deps.chat.name,
      actor_role: 'system',
      approval_request_id: record.request_id,
      detail: { channel: this.deps.approvalChannel, message_id: posted.messageId },
    });

    return notified;
  }

  /**
   * 詳細確認(D-2 ステップ 2)。
   * ボタン押下は最終承認ではない。ここでは nonce を消費しない。
   */
  async openDetails(args: {
    requestId: string;
    platformUserId: string;
    cardVersion: number;
  }): Promise<{ ok: true; details: ApprovalDetails } | { ok: false; refusal: ApprovalRefusal; message: string }> {
    const identity = await this.deps.identities.resolve(args.platformUserId);
    if (!identity) {
      return { ok: false, refusal: 'unknown_identity', message: '内部の本人に対応づけられない利用者' };
    }

    const request = await this.deps.store.getApprovalRequest(args.requestId);
    if (!request) return { ok: false, refusal: 'not_found', message: '承認要求が存在しない' };

    if (request.status !== 'pending') {
      return { ok: false, refusal: 'already_processed', message: '処理済みの承認要求' };
    }
    if (request.packet.card_version !== args.cardVersion) {
      return { ok: false, refusal: 'stale_card', message: '古いカードからの操作' };
    }
    if (this.isExpired(request.packet)) {
      await this.markExpired(request);
      return { ok: false, refusal: 'expired', message: '承認期限を過ぎている' };
    }
    if (identity.role !== 'approver') {
      await this.recordRejectedAction(request, identity, 'forbidden_role');
      return { ok: false, refusal: 'forbidden_role', message: '承認ロールを持たない利用者' };
    }

    const packet = request.packet;
    return {
      ok: true,
      details: {
        packet,
        status: request.status,
        finalConfirmation: {
          operation: packet.operation,
          target: packet.granted_scope.target,
          recipients: packet.granted_scope.recipients,
          previewExcerpt: previewExcerpt(packet.preview, 600, packet.granted_scope.recipients),
          constraints: packet.constraints,
          rollback: packet.rollback,
        },
      },
    };
  }

  /**
   * 最終確定(D-2 ステップ 3-4、D-3 手順 3-8)。
   * ここで初めて nonce を消費し、承認を原子的に記録する。
   */
  async submitDecision(args: {
    requestId: string;
    platformUserId: string;
    cardVersion: number;
    nonce: string;
    decision: unknown;
  }): Promise<ApprovalOutcome> {
    /* 手順 2: 本人・ロールの解決 */
    const identity = await this.deps.identities.resolve(args.platformUserId);
    if (!identity) {
      return { ok: false, refusal: 'unknown_identity', message: '内部の本人に対応づけられない利用者' };
    }

    const parsedDecision = approvalDecisionSchema.safeParse(args.decision);
    if (!parsedDecision.success) {
      return { ok: false, refusal: 'invalid_decision', message: '判断入力が不正' };
    }
    const decisionInput = parsedDecision.data;

    /* 手順 3: 正本の確認(状態・期限・カード版数・nonce) */
    const current = await this.deps.store.getApprovalRequest(args.requestId);
    if (!current) return { ok: false, refusal: 'not_found', message: '承認要求が存在しない' };
    if (current.status !== 'pending' || current.nonce_consumed) {
      return { ok: false, refusal: 'already_processed', message: '処理済みの承認要求' };
    }
    if (current.packet.card_version !== args.cardVersion || current.packet.nonce !== args.nonce) {
      await this.recordRejectedAction(current, identity, 'stale_card');
      return { ok: false, refusal: 'stale_card', message: '古いカードまたは無効な nonce' };
    }
    if (this.isExpired(current.packet)) {
      await this.markExpired(current);
      return { ok: false, refusal: 'expired', message: '承認期限を過ぎている' };
    }

    /* 手順 4: ロールの確認 */
    if (identity.role !== 'approver') {
      await this.recordRejectedAction(current, identity, 'forbidden_role');
      return { ok: false, refusal: 'forbidden_role', message: '承認ロールを持たない利用者' };
    }

    /* 手順 5: 承認条件が scope を拡張していないか */
    const scopeCheck = narrowScope(current.packet, decisionInput);
    if (!scopeCheck.ok) {
      await this.recordRejectedAction(current, identity, 'scope_expansion');
      return { ok: false, refusal: 'scope_expansion', message: scopeCheck.message };
    }

    /* 手順 6-7: 決定の原子的記録と、許可 scope に限った実行 */
    return this.deps.store.transaction(async (tx) => {
      const claimed = await tx.claimApprovalRequest({
        requestId: args.requestId,
        expectedStatus: 'pending',
        cardVersion: args.cardVersion,
        nonce: args.nonce,
      });
      if (!claimed) {
        // 同時操作に敗れた側。二重に決定を記録しない。
        return { ok: false as const, refusal: 'already_processed' as const, message: '同時操作により処理済み' };
      }

      const caseRecord = await tx.getCase(claimed.case_id);
      if (!caseRecord) {
        throw new Error(`案件が見つかりません: ${claimed.case_id}`);
      }

      const decisionRecord: ApprovalDecisionRecord = {
        decision_id: this.deps.ids.next('dec'),
        request_id: claimed.request_id,
        case_id: claimed.case_id,
        decision: decisionInput.decision,
        reason: decisionInput.reason,
        conditions: decisionInput.conditions,
        decided_by: identity.userId,
        decided_by_role: identity.role,
        decided_at: this.deps.clock.now().toISOString(),
        granted_scope: scopeCheck.scope,
      };
      await tx.insertApprovalDecision(decisionRecord);

      const updated: ApprovalRequestRecord = {
        ...claimed,
        status:
          decisionInput.decision === 'approved'
            ? 'approved'
            : decisionInput.decision === 'approved_with_conditions'
              ? 'approved_with_conditions'
              : decisionInput.decision === 'returned'
                ? 'returned'
                : 'rejected',
        updated_at: this.deps.clock.now().toISOString(),
      };
      await tx.updateApprovalRequest(updated);

      await this.deps.audit.record(tx, {
        case_id: claimed.case_id,
        event_type: 'approval.decided',
        actor: identity.userId,
        actor_role: identity.role,
        approval_request_id: claimed.request_id,
        decision: decisionInput.decision,
        detail: {
          reason: decisionInput.reason,
          conditions: decisionInput.conditions,
          granted_scope: scopeCheck.scope,
        },
      });

      const approved =
        decisionInput.decision === 'approved' || decisionInput.decision === 'approved_with_conditions';
      const executions = approved
        ? await this.deps.resumeAfterApproval(tx, {
            caseRecord,
            request: updated,
            decision: decisionRecord,
          })
        : [];

      /* 手順 8: 元カードを最終状態へ更新 */
      await this.updateCard(updated, finalCardStateFor(decisionInput, identity));

      return { ok: true as const, request: updated, decision: decisionRecord, executions };
    });
  }

  /* ---------------- 補助 ---------------- */

  private isExpired(packet: ApprovalPacket): boolean {
    return new Date(packet.expires_at).getTime() <= this.deps.clock.now().getTime();
  }

  private async markExpired(request: ApprovalRequestRecord): Promise<void> {
    if (request.status !== 'pending') return;
    const updated: ApprovalRequestRecord = {
      ...request,
      status: 'expired',
      updated_at: this.deps.clock.now().toISOString(),
    };
    await this.deps.store.transaction(async (tx) => {
      await tx.updateApprovalRequest(updated);
      await this.deps.audit.record(tx, {
        case_id: request.case_id,
        event_type: 'approval.action_rejected',
        actor: 'approval_service',
        actor_role: 'system',
        approval_request_id: request.request_id,
        decision: 'expired',
        detail: { expires_at: request.packet.expires_at },
      });
    });
    await this.updateCard(updated, { kind: 'expired' });
  }

  private async recordRejectedAction(
    request: ApprovalRequestRecord,
    identity: InternalIdentity,
    reason: ApprovalRefusal,
  ): Promise<void> {
    await this.deps.store.transaction(async (tx) => {
      await this.deps.audit.record(tx, {
        case_id: request.case_id,
        event_type: 'approval.action_rejected',
        actor: identity.userId,
        actor_role: identity.role,
        approval_request_id: request.request_id,
        decision: `refused:${reason}`,
        detail: { role: identity.role, required_role: request.packet.required_role },
      });
    });
  }

  private async updateCard(request: ApprovalRequestRecord, finalState: FinalCardState): Promise<void> {
    if (!request.chat_message_id) return;
    await this.deps.chat.updateApprovalCard({
      channel: this.deps.approvalChannel,
      messageId: request.chat_message_id,
      packet: request.packet,
      finalState,
    });
  }
}

/**
 * 条件付き承認が scope を拡張していないかを確認し、絞り込んだ scope を返す。
 * 宛先の追加、対象の変更、条件文への新しい宛先の記載はすべて拡張とみなす。
 */
export function narrowScope(
  packet: ApprovalPacket,
  decision: ApprovalDecisionInput,
):
  | { ok: true; scope: { operation: ApprovalPacket['operation']; target: string; recipients: string[] } }
  | { ok: false; message: string } {
  const base = packet.granted_scope;
  let recipients = [...base.recipients];
  let target = base.target;

  if (decision.scope_override?.recipients) {
    const requested = decision.scope_override.recipients;
    const extra = requested.filter((r) => !base.recipients.includes(r));
    if (extra.length > 0) {
      return { ok: false, message: `承認条件が宛先を追加している: ${extra.join(', ')}` };
    }
    recipients = requested;
  }

  if (decision.scope_override?.target && decision.scope_override.target !== base.target) {
    return { ok: false, message: '承認条件が対象を変更している' };
  }

  // 条件文に元の scope に無い宛先が書かれていないか。
  const mentioned = decision.conditions
    .join('\n')
    .match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g);
  if (mentioned) {
    const extra = mentioned.filter((r) => !base.recipients.includes(r));
    if (extra.length > 0) {
      return { ok: false, message: `承認条件が scope 外の宛先を含む: ${extra.join(', ')}` };
    }
  }

  return { ok: true, scope: { operation: base.operation, target, recipients } };
}

function finalCardStateFor(
  decision: ApprovalDecisionInput,
  identity: InternalIdentity,
): FinalCardState {
  switch (decision.decision) {
    case 'approved':
      return { kind: 'approved', conditions: [], decidedBy: identity.displayName };
    case 'approved_with_conditions':
      return {
        kind: 'approved_with_conditions',
        conditions: decision.conditions,
        decidedBy: identity.displayName,
      };
    case 'returned':
      return { kind: 'returned', reason: decision.reason, decidedBy: identity.displayName };
    case 'rejected':
      return { kind: 'rejected', reason: decision.reason, decidedBy: identity.displayName };
  }
}
