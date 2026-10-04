/**
 * Slack 連携(FR-030〜FR-034、手順書 D-1 / D-2)。
 *
 * カードは Block Kit で構成する。表示するのは
 * 判断タイトル・リスク・期限・対象・根拠要約・制約と、最大 3 つの操作だけ。
 * 本文全文、個人情報、認証情報、実行トークン、実行権限そのものはカードに載せない。
 *
 * ボタンの value には `request_id` と `card_version` しか入れない。
 * ワンタイム値(nonce)はサーバーがモーダルを開くときに `private_metadata` へ入れる。
 * したがってカードだけを再送しても最終確定はできない。
 */

import { createHmac, timingSafeEqual } from 'node:crypto';
import type { ApprovalNotification, ChatAdapter, FinalCardState } from '../../ports/chat.js';
import type { ApprovalPacket } from '../../domain/schemas.js';
import type { ApprovalDetails } from '../../approval/approval-service.js';
import { previewExcerpt } from '../../security/redact.js';

/* ------------------------------------------------------------------ */
/* 署名検証(FR-034)                                                    */
/* ------------------------------------------------------------------ */

export interface SignatureVerificationInput {
  signingSecret: string;
  /** X-Slack-Request-Timestamp */
  timestamp: string;
  /** X-Slack-Signature */
  signature: string;
  /** 生のリクエストボディ。パース前の文字列でなければならない。 */
  rawBody: string;
  /** 検証時刻(Unix 秒)。 */
  nowUnixSeconds: number;
  /** 許容するずれ。既定は 5 分。 */
  toleranceSeconds?: number;
}

export type SignatureVerdict =
  | { valid: true }
  | { valid: false; reason: 'stale_timestamp' | 'bad_timestamp' | 'signature_mismatch' };

/**
 * Slack からのリクエストであることを検証する。
 *
 * `v0:{timestamp}:{rawBody}` を signing secret で HMAC-SHA256 し、
 * `v0=` 付きの 16 進文字列を定数時間比較する。
 * タイムスタンプが古いリクエストはリプレイとみなして拒否する。
 */
export function verifySlackSignature(input: SignatureVerificationInput): SignatureVerdict {
  const tolerance = input.toleranceSeconds ?? 60 * 5;
  const timestamp = Number(input.timestamp);
  if (!Number.isFinite(timestamp)) return { valid: false, reason: 'bad_timestamp' };
  if (Math.abs(input.nowUnixSeconds - timestamp) > tolerance) {
    return { valid: false, reason: 'stale_timestamp' };
  }

  const expected = `v0=${createHmac('sha256', input.signingSecret)
    .update(`v0:${input.timestamp}:${input.rawBody}`)
    .digest('hex')}`;

  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(input.signature ?? '', 'utf8');
  if (a.length !== b.length) return { valid: false, reason: 'signature_mismatch' };
  return timingSafeEqual(a, b) ? { valid: true } : { valid: false, reason: 'signature_mismatch' };
}

/* ------------------------------------------------------------------ */
/* Slack Web API の最小クライアント                                     */
/* ------------------------------------------------------------------ */

export interface SlackClient {
  postMessage(args: {
    channel: string;
    text: string;
    blocks: unknown[];
  }): Promise<{ ts: string }>;
  updateMessage(args: {
    channel: string;
    ts: string;
    text: string;
    blocks: unknown[];
  }): Promise<void>;
  openView(args: { triggerId: string; view: unknown }): Promise<void>;
}

export class HttpSlackClient implements SlackClient {
  constructor(
    private readonly botToken: string,
    private readonly fetchImpl: typeof fetch = fetch,
  ) {}

  async postMessage(args: { channel: string; text: string; blocks: unknown[] }): Promise<{ ts: string }> {
    const body = await this.call('chat.postMessage', args);
    return { ts: String(body.ts) };
  }

  async updateMessage(args: {
    channel: string;
    ts: string;
    text: string;
    blocks: unknown[];
  }): Promise<void> {
    await this.call('chat.update', args);
  }

  async openView(args: { triggerId: string; view: unknown }): Promise<void> {
    await this.call('views.open', { trigger_id: args.triggerId, view: args.view });
  }

  private async call(method: string, payload: Record<string, unknown>): Promise<Record<string, any>> {
    const response = await this.fetchImpl(`https://slack.com/api/${method}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        Authorization: `Bearer ${this.botToken}`,
      },
      body: JSON.stringify(payload),
    });
    const body = (await response.json()) as Record<string, any>;
    if (!body.ok) throw new Error(`Slack ${method} に失敗: ${body.error ?? response.status}`);
    return body;
  }
}

/* ------------------------------------------------------------------ */
/* ChatAdapter 実装                                                     */
/* ------------------------------------------------------------------ */

export const SLACK_ACTION_OPEN_DETAILS = 'approval_open_details';
export const SLACK_ACTION_RETURN = 'approval_return';
export const SLACK_ACTION_OPEN_SAFE_VIEW = 'approval_open_safe_view';
export const SLACK_CALLBACK_DECISION = 'approval_decision_modal';
export const SLACK_CALLBACK_CONFIRM = 'approval_confirm_modal';

export class SlackChatAdapter implements ChatAdapter {
  readonly name = 'slack';

  constructor(
    private readonly client: SlackClient,
    /** 詳細画面の URL。SSO で保護された管理画面を指す。 */
    private readonly detailBaseUrl: string,
  ) {}

  async postApprovalRequest(notification: ApprovalNotification): Promise<{ messageId: string }> {
    const { packet } = notification;
    const posted = await this.client.postMessage({
      channel: notification.channel,
      // アクセシビリティ:リスク・期限・操作をトップレベル text にも書く。
      text: buildFallbackText(packet),
      blocks: buildApprovalBlocks(packet, notification.evidenceSummary, this.detailBaseUrl),
    });
    return { messageId: posted.ts };
  }

  async updateApprovalCard(args: {
    channel: string;
    messageId: string;
    packet: ApprovalPacket;
    finalState: FinalCardState;
  }): Promise<void> {
    await this.client.updateMessage({
      channel: args.channel,
      ts: args.messageId,
      text: `${buildFallbackText(args.packet)} — ${finalStateLabel(args.finalState)}`,
      blocks: buildFinalBlocks(args.packet, args.finalState),
    });
  }

  /** 詳細確認モーダルを開く(D-2 ステップ 2)。 */
  async openDetailModal(args: { triggerId: string; details: ApprovalDetails }): Promise<void> {
    await this.client.openView({
      triggerId: args.triggerId,
      view: buildDecisionModal(args.details),
    });
  }
}

/* ------------------------------------------------------------------ */
/* Block Kit の組み立て                                                 */
/* ------------------------------------------------------------------ */

const RISK_LABEL: Record<string, string> = {
  green: '🟢 GREEN(可逆・社内)',
  yellow: '🟡 YELLOW(対外・要承認)',
  red: '🔴 RED(不可逆・人間主導)',
};

export function buildFallbackText(packet: ApprovalPacket): string {
  return [
    `[承認依頼] ${packet.operation}`,
    `リスク: ${RISK_LABEL[packet.risk] ?? packet.risk}`,
    `期限: ${packet.expires_at}`,
    '操作: 承認へ進む / 差戻す / 安全な詳細を開く',
  ].join(' / ');
}

/**
 * 通知カード(FR-031)。
 * 表示は 判断タイトル・リスク・期限・対象・根拠要約・制約、操作は最大 3 つ。
 */
export function buildApprovalBlocks(
  packet: ApprovalPacket,
  evidenceSummary: readonly string[],
  detailBaseUrl: string,
): unknown[] {
  const permitted = packet.granted_scope.recipients;
  return [
    {
      type: 'header',
      text: { type: 'plain_text', text: `承認依頼: ${packet.operation}`, emoji: true },
    },
    {
      type: 'section',
      fields: [
        { type: 'mrkdwn', text: `*リスク*\n${RISK_LABEL[packet.risk] ?? packet.risk}` },
        { type: 'mrkdwn', text: `*期限*\n${packet.expires_at}` },
        { type: 'mrkdwn', text: `*対象*\n${packet.granted_scope.target}` },
        { type: 'mrkdwn', text: `*案件*\n${packet.case_id}` },
      ],
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*根拠要約*\n${
          evidenceSummary.length > 0
            ? evidenceSummary
                .slice(0, 3)
                .map((s) => `• ${previewExcerpt(s, 120, permitted)}`)
                .join('\n')
            : '• (根拠なし。承認前に確認が必要)'
        }`,
      },
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*制約*\n${packet.constraints.map((c) => `• ${c}`).join('\n')}`,
      },
    },
    {
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: '本文全文と根拠の詳細は、このカードではなく詳細画面で確認してください。',
        },
      ],
    },
    {
      type: 'actions',
      elements: [
        {
          type: 'button',
          style: 'primary',
          text: { type: 'plain_text', text: '承認へ進む', emoji: true },
          action_id: SLACK_ACTION_OPEN_DETAILS,
          // 実行権限やワンタイム値は載せない。参照子だけを持たせる。
          value: JSON.stringify({ request_id: packet.request_id, card_version: packet.card_version }),
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: '差戻す', emoji: true },
          action_id: SLACK_ACTION_RETURN,
          value: JSON.stringify({ request_id: packet.request_id, card_version: packet.card_version }),
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: '安全な詳細を開く', emoji: true },
          action_id: SLACK_ACTION_OPEN_SAFE_VIEW,
          url: `${detailBaseUrl}/cases/${packet.case_id}/approvals/${packet.request_id}`,
        },
      ],
    },
  ];
}

/** 判断フォーム(D-2 ステップ 3)。ここで初めて nonce を渡す。 */
export function buildDecisionModal(details: ApprovalDetails): unknown {
  const { packet, finalConfirmation } = details;
  return {
    type: 'modal',
    callback_id: SLACK_CALLBACK_DECISION,
    private_metadata: JSON.stringify({
      request_id: packet.request_id,
      card_version: packet.card_version,
      nonce: packet.nonce,
    }),
    title: { type: 'plain_text', text: '承認の判断', emoji: true },
    submit: { type: 'plain_text', text: '最終確認へ', emoji: true },
    close: { type: 'plain_text', text: '閉じる', emoji: true },
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: [
            `*行為*: ${finalConfirmation.operation}`,
            `*対象*: ${finalConfirmation.target}`,
            `*宛先*: ${finalConfirmation.recipients.join(', ') || '(なし)'}`,
            `*ロールバック*: ${finalConfirmation.rollback}`,
          ].join('\n'),
        },
      },
      {
        type: 'section',
        text: { type: 'mrkdwn', text: `*プレビュー*\n\`\`\`${finalConfirmation.previewExcerpt}\`\`\`` },
      },
      {
        type: 'input',
        block_id: 'decision',
        label: { type: 'plain_text', text: '判断', emoji: true },
        element: {
          type: 'static_select',
          action_id: 'value',
          options: [
            { text: { type: 'plain_text', text: '承認' }, value: 'approved' },
            { text: { type: 'plain_text', text: '条件付き承認' }, value: 'approved_with_conditions' },
            { text: { type: 'plain_text', text: '差戻し' }, value: 'returned' },
            { text: { type: 'plain_text', text: '却下' }, value: 'rejected' },
          ],
        },
      },
      {
        type: 'input',
        block_id: 'reason',
        label: { type: 'plain_text', text: '理由', emoji: true },
        element: { type: 'plain_text_input', action_id: 'value', multiline: true },
      },
      {
        type: 'input',
        block_id: 'conditions',
        optional: true,
        label: { type: 'plain_text', text: '条件(1 行 1 件)', emoji: true },
        element: { type: 'plain_text_input', action_id: 'value', multiline: true },
      },
    ],
  };
}

/** 最終確定画面(D-2 ステップ 4)。宛先・本文・範囲を最後にもう一度見せる。 */
export function buildConfirmationView(
  details: ApprovalDetails,
  decision: { decision: string; reason: string; conditions: readonly string[] },
): unknown {
  const { packet, finalConfirmation } = details;
  return {
    type: 'modal',
    callback_id: SLACK_CALLBACK_CONFIRM,
    private_metadata: JSON.stringify({
      request_id: packet.request_id,
      card_version: packet.card_version,
      nonce: packet.nonce,
      decision,
    }),
    title: { type: 'plain_text', text: '最終確認', emoji: true },
    submit: { type: 'plain_text', text: 'この内容で確定', emoji: true },
    close: { type: 'plain_text', text: '戻る', emoji: true },
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: [
            `*判断*: ${decision.decision}`,
            `*宛先*: ${finalConfirmation.recipients.join(', ') || '(なし)'}`,
            `*対象*: ${finalConfirmation.target}`,
            `*許可される操作*: ${finalConfirmation.operation} のみ`,
            `*条件*: ${decision.conditions.join(' / ') || '(なし)'}`,
          ].join('\n'),
        },
      },
      {
        type: 'section',
        text: { type: 'mrkdwn', text: `*本文(抜粋)*\n\`\`\`${finalConfirmation.previewExcerpt}\`\`\`` },
      },
      {
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: '確定すると、承認記録が残り、許可された範囲のみが実行キューへ渡ります。',
          },
        ],
      },
    ],
  };
}

/** 最終状態へ更新したカード(FR-033)。 */
export function buildFinalBlocks(packet: ApprovalPacket, finalState: FinalCardState): unknown[] {
  return [
    {
      type: 'header',
      text: { type: 'plain_text', text: `承認依頼: ${packet.operation}`, emoji: true },
    },
    {
      type: 'section',
      text: { type: 'mrkdwn', text: `*状態*: ${finalStateLabel(finalState)}` },
    },
    {
      type: 'context',
      elements: [
        { type: 'mrkdwn', text: `案件 ${packet.case_id} / 要求 ${packet.request_id}` },
      ],
    },
  ];
}

export function finalStateLabel(state: FinalCardState): string {
  switch (state.kind) {
    case 'approved':
      return `承認済み(${state.decidedBy})`;
    case 'approved_with_conditions':
      return `条件付き承認(${state.decidedBy} / 条件: ${state.conditions.join(' / ') || 'なし'})`;
    case 'returned':
      return `差戻し(${state.decidedBy}): ${state.reason}`;
    case 'rejected':
      return `却下(${state.decidedBy}): ${state.reason}`;
    case 'expired':
      return '期限切れ';
    case 'already_processed':
      return '処理済み';
  }
}
