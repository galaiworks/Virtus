/**
 * Slack 操作の受信(FR-032 / FR-034、手順書 D-3)。
 *
 * カードが返す `approve` をそのまま実行しない。
 * 受信時に必ず署名・タイムスタンプを検証し、そのあと ApprovalService が
 * 本人・ロール・状態・期限・カード版数・nonce・scope を再検証する。
 *
 * 可用性要件より、対話イベントは速やかに応答する。
 * 長時間の処理はここでは行わない。
 */

import type { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import type { App } from '../app.js';
import { verifySlackSignature } from '../adapters/chat/slack-adapter.js';
import {
  SLACK_ACTION_OPEN_DETAILS,
  SLACK_ACTION_RETURN,
  SLACK_CALLBACK_CONFIRM,
  SLACK_CALLBACK_DECISION,
  SlackChatAdapter,
  buildConfirmationView,
} from '../adapters/chat/slack-adapter.js';
import type { ApprovalRefusal } from '../approval/approval-service.js';

interface SlackInteractionBody {
  type: string;
  user?: { id: string };
  trigger_id?: string;
  actions?: { action_id: string; value?: string }[];
  view?: {
    callback_id: string;
    private_metadata: string;
    state?: { values: Record<string, Record<string, { value?: string; selected_option?: { value: string } }>> };
  };
}

/** 利用者に返すメッセージ。内部の詳細は出さない。 */
const REFUSAL_MESSAGE: Record<ApprovalRefusal, string> = {
  not_found: 'この承認要求は見つかりません。',
  unknown_identity: 'この操作を行う権限が確認できません。',
  forbidden_role: '承認ロールがないため操作できません。',
  expired: '期限切れです。',
  already_processed: '処理済みです。',
  stale_card: '古いカードです。最新の通知から操作してください。',
  invalid_decision: '入力内容が不正です。',
  scope_expansion: '承認条件が元の許可範囲を超えています。',
  case_not_found: '案件が見つかりません。',
};

export function registerSlackRoutes(server: FastifyInstance, app: App): void {
  server.post('/slack/interactions', async (request: FastifyRequest, reply: FastifyReply) => {
    /* 手順 1: プラットフォーム由来の正規リクエストか。 */
    const signingSecret = app.config.chat.slack.signingSecret;
    if (!signingSecret) {
      return reply.code(503).send({ error: 'Slack 連携が未設定です' });
    }

    const rawBody = (request as FastifyRequest & { rawBody?: string }).rawBody ?? '';
    const verdict = verifySlackSignature({
      signingSecret,
      timestamp: String(request.headers['x-slack-request-timestamp'] ?? ''),
      signature: String(request.headers['x-slack-signature'] ?? ''),
      rawBody,
      nowUnixSeconds: app.clock.unixSeconds(),
    });
    if (!verdict.valid) {
      request.log.warn({ reason: verdict.reason }, 'Slack 署名検証に失敗したため操作を拒否した');
      return reply.code(401).send({ error: 'invalid signature' });
    }

    const payload = parsePayload(rawBody);
    if (!payload) return reply.code(400).send({ error: 'invalid payload' });

    const platformUserId = payload.user?.id ?? '';

    if (payload.type === 'block_actions') {
      return handleBlockActions(app, payload, platformUserId, reply);
    }
    if (payload.type === 'view_submission') {
      return handleViewSubmission(app, payload, platformUserId, reply);
    }

    return reply.code(200).send();
  });
}

async function handleBlockActions(
  app: App,
  payload: SlackInteractionBody,
  platformUserId: string,
  reply: FastifyReply,
): Promise<FastifyReply> {
  const action = payload.actions?.[0];
  if (!action) return reply.code(200).send();
  if (action.action_id !== SLACK_ACTION_OPEN_DETAILS && action.action_id !== SLACK_ACTION_RETURN) {
    // 「安全な詳細を開く」は URL リンクのため、サーバー処理は不要。
    return reply.code(200).send();
  }

  const ref = safeJson<{ request_id?: string; card_version?: number }>(action.value);
  if (!ref?.request_id || typeof ref.card_version !== 'number') {
    return reply.code(200).send({ text: '操作に必要な情報が不足しています。' });
  }

  /* 手順 2-4: 本人・ロール・状態・期限・カード版数の再検証。nonce はここでは使わない。 */
  const details = await app.approvals.openDetails({
    requestId: ref.request_id,
    platformUserId,
    cardVersion: ref.card_version,
  });
  if (!details.ok) {
    return reply.code(200).send({ text: REFUSAL_MESSAGE[details.refusal] });
  }

  if (app.chat instanceof SlackChatAdapter && payload.trigger_id) {
    await app.chat.openDetailModal({ triggerId: payload.trigger_id, details: details.details });
  }
  return reply.code(200).send();
}

async function handleViewSubmission(
  app: App,
  payload: SlackInteractionBody,
  platformUserId: string,
  reply: FastifyReply,
): Promise<FastifyReply> {
  const view = payload.view;
  if (!view) return reply.code(200).send();

  const metadata = safeJson<{
    request_id?: string;
    card_version?: number;
    nonce?: string;
    decision?: { decision: string; reason: string; conditions: string[] };
  }>(view.private_metadata);
  if (!metadata?.request_id || typeof metadata.card_version !== 'number' || !metadata.nonce) {
    return reply.code(200).send({
      response_action: 'errors',
      errors: { decision: '操作に必要な情報が不足しています。' },
    });
  }

  /* ステップ 3 → 4: 判断フォームの送信では確定せず、最終確認画面を挟む(FR-032)。 */
  if (view.callback_id === SLACK_CALLBACK_DECISION) {
    const decision = {
      decision: readSelect(view, 'decision') ?? 'returned',
      reason: readInput(view, 'reason') ?? '',
      conditions: (readInput(view, 'conditions') ?? '')
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0),
    };
    if (decision.reason.length === 0) {
      return reply.code(200).send({
        response_action: 'errors',
        errors: { reason: '理由を入力してください。' },
      });
    }

    const details = await app.approvals.openDetails({
      requestId: metadata.request_id,
      platformUserId,
      cardVersion: metadata.card_version,
    });
    if (!details.ok) {
      return reply.code(200).send({
        response_action: 'errors',
        errors: { decision: REFUSAL_MESSAGE[details.refusal] },
      });
    }

    return reply
      .code(200)
      .send({ response_action: 'push', view: buildConfirmationView(details.details, decision) });
  }

  /* 最終確定。ここで初めて nonce を消費し、承認を記録する。 */
  if (view.callback_id === SLACK_CALLBACK_CONFIRM) {
    const outcome = await app.approvals.submitDecision({
      requestId: metadata.request_id,
      platformUserId,
      cardVersion: metadata.card_version,
      nonce: metadata.nonce,
      decision: metadata.decision ?? {},
    });
    if (!outcome.ok) {
      return reply.code(200).send({
        response_action: 'errors',
        errors: { decision: REFUSAL_MESSAGE[outcome.refusal] },
      });
    }
    return reply.code(200).send({ response_action: 'clear' });
  }

  return reply.code(200).send();
}

/* ---------------- 補助 ---------------- */

function parsePayload(rawBody: string): SlackInteractionBody | null {
  const params = new URLSearchParams(rawBody);
  const payload = params.get('payload');
  if (!payload) return null;
  return safeJson<SlackInteractionBody>(payload);
}

function safeJson<T>(value: string | undefined): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

function readInput(view: NonNullable<SlackInteractionBody['view']>, blockId: string): string | null {
  return view.state?.values?.[blockId]?.value?.value ?? null;
}

function readSelect(view: NonNullable<SlackInteractionBody['view']>, blockId: string): string | null {
  return view.state?.values?.[blockId]?.value?.selected_option?.value ?? null;
}
