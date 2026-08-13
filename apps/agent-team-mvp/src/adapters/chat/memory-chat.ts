/**
 * インメモリのチャットアダプタ。
 *
 * 未選択のチャット(FR-030)を「未実装」として扱いつつ、
 * 承認フローのテスト・評価をチャット基盤なしで回すために使う。
 */

import type {
  ApprovalNotification,
  ChatAdapter,
  FinalCardState,
} from '../../ports/chat.js';
import type { ApprovalPacket } from '../../domain/schemas.js';

export interface PostedCard {
  messageId: string;
  channel: string;
  packet: ApprovalPacket;
  evidenceSummary: readonly string[];
  finalState: FinalCardState | null;
  updates: number;
}

export class MemoryChatAdapter implements ChatAdapter {
  readonly name = 'memory';

  readonly cards = new Map<string, PostedCard>();
  private counter = 0;

  async postApprovalRequest(notification: ApprovalNotification): Promise<{ messageId: string }> {
    this.counter += 1;
    const messageId = `msg_${String(this.counter).padStart(4, '0')}`;
    this.cards.set(messageId, {
      messageId,
      channel: notification.channel,
      packet: notification.packet,
      evidenceSummary: notification.evidenceSummary,
      finalState: null,
      updates: 0,
    });
    return { messageId };
  }

  async updateApprovalCard(args: {
    channel: string;
    messageId: string;
    packet: ApprovalPacket;
    finalState: FinalCardState;
  }): Promise<void> {
    const card = this.cards.get(args.messageId);
    if (!card) throw new Error(`カードが見つかりません: ${args.messageId}`);
    card.finalState = args.finalState;
    card.updates += 1;
  }

  find(requestId: string): PostedCard | undefined {
    return [...this.cards.values()].find((c) => c.packet.request_id === requestId);
  }
}

/**
 * 未選択チャットの実装。
 * FR-030 より、MVP では Slack と Teams を同時に実装しない。
 * 選ばれなかった側はこのアダプタを割り当て、呼び出されたら明示的に失敗させる。
 */
export class UnimplementedChatAdapter implements ChatAdapter {
  constructor(readonly name: 'slack' | 'teams') {}

  async postApprovalRequest(): Promise<{ messageId: string }> {
    throw new Error(`${this.name} は MVP で未実装のチャットです(FR-030)`);
  }

  async updateApprovalCard(): Promise<void> {
    throw new Error(`${this.name} は MVP で未実装のチャットです(FR-030)`);
  }
}
