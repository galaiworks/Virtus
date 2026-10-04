/**
 * チャットのポート(FR-030)。
 *
 * MVP は Slack か Teams の一方だけを有効にする。
 * どちらを選んでもこの契約は変えない。未選択のチャットは未実装として扱う。
 */

import type { ApprovalPacket } from '../domain/schemas.js';

export interface ApprovalNotification {
  packet: ApprovalPacket;
  /** 通知先。DM または限定チャンネル。 */
  channel: string;
  /** 根拠要約。原文全文は載せない(D-2)。 */
  evidenceSummary: readonly string[];
}

export type FinalCardState =
  | { kind: 'approved'; conditions: readonly string[]; decidedBy: string }
  | { kind: 'approved_with_conditions'; conditions: readonly string[]; decidedBy: string }
  | { kind: 'returned'; reason: string; decidedBy: string }
  | { kind: 'rejected'; reason: string; decidedBy: string }
  | { kind: 'expired' }
  | { kind: 'already_processed' };

export interface ChatAdapter {
  readonly name: 'slack' | 'teams' | 'memory';
  /** 承認依頼カードを送る。戻り値はカード更新に使うメッセージ ID。 */
  postApprovalRequest(notification: ApprovalNotification): Promise<{ messageId: string }>;
  /** 元カード・スレッドを最終状態に更新する(FR-033)。 */
  updateApprovalCard(args: {
    channel: string;
    messageId: string;
    packet: ApprovalPacket;
    finalState: FinalCardState;
  }): Promise<void>;
}
