/**
 * 環境設定。
 *
 * 非機能要件「セキュリティ」より、API キー・署名シークレット・アクセストークンは
 * サーバー側の環境変数からのみ読む。クライアント・カード・ログへ出さない。
 */

import { z } from 'zod';
import type { InternalIdentity } from './ports/identity.js';

export type LlmProvider = 'anthropic' | 'scripted';
export type ChatProvider = 'slack' | 'teams' | 'memory';
export type StoreProvider = 'postgres' | 'memory';

/**
 * チャット利用者 ID → 内部の本人・ロール(手順書 D-3 手順 2)。
 *
 * カードのボタン値ではなく、この表の解決結果だけでロールを判定する。
 * 表に無い利用者の操作は `unknown_identity` として拒否される。
 */
export const identityMappingSchema = z.object({
  /** チャットプラットフォーム上の利用者 ID(Slack なら U01ABC2DEF 形式)。 */
  platform_user_id: z.string().min(1),
  /** 内部の利用者 ID。監査ログに残る。 */
  user_id: z.string().min(1),
  display_name: z.string().min(1),
  role: z.enum([
    'requester',
    'process_owner',
    'approver',
    'data_owner',
    'ai_ops',
    'security',
    'executive',
  ]),
});
export type IdentityMapping = z.infer<typeof identityMappingSchema>;

export interface AppConfig {
  port: number;
  store: StoreProvider;
  databaseUrl: string | null;
  llm: {
    provider: LlmProvider;
    apiKey: string | null;
    model: string;
  };
  chat: {
    /** MVP はどちらか一方だけを有効にする(FR-030)。 */
    provider: ChatProvider;
    slack: {
      botToken: string | null;
      signingSecret: string | null;
      approvalChannel: string;
    };
  };
  /**
   * 承認・判断を行える利用者の表。
   * 空のまま Slack を有効にすると誰も承認できないため、起動時に落とす。
   */
  identities: IdentityMapping[];
  /** 本人・ロール表の読み取りに失敗した理由。起動時に報告して落とす。 */
  identitiesError: string | null;
  /** SSO で保護された管理画面のベース URL。カードのリンク先。 */
  adminBaseUrl: string;
  approval: {
    ttlHours: number;
  };
  knowledge: {
    staleAfterDays: number;
  };
}

function readInt(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

/**
 * `APPROVAL_IDENTITIES` を読む。JSON 配列を期待する。
 *
 * 壊れた値を黙って無視すると「承認者がいないのに起動する」状態になるため、
 * 解析に失敗した場合は空配列を返し、validateConfig 側で起動を止める。
 */
export function parseIdentities(raw: string | undefined): {
  identities: IdentityMapping[];
  error: string | null;
} {
  if (!raw || raw.trim().length === 0) return { identities: [], error: null };

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { identities: [], error: 'APPROVAL_IDENTITIES が JSON として解析できない' };
  }

  const result = z.array(identityMappingSchema).safeParse(parsed);
  if (!result.success) {
    const detail = result.error.issues
      .map((issue) => `${issue.path.join('.')}: ${issue.message}`)
      .join('; ');
    return { identities: [], error: `APPROVAL_IDENTITIES の形式が不正: ${detail}` };
  }

  const duplicates = result.data
    .map((entry) => entry.platform_user_id)
    .filter((id, index, all) => all.indexOf(id) !== index);
  if (duplicates.length > 0) {
    return {
      identities: [],
      error: `APPROVAL_IDENTITIES に重複した platform_user_id がある: ${[...new Set(duplicates)].join(', ')}`,
    };
  }

  return { identities: result.data, error: null };
}

/** 設定表を IdentityResolver が使う形へ変換する。 */
export function toIdentityTable(
  identities: readonly IdentityMapping[],
): Record<string, InternalIdentity> {
  return Object.fromEntries(
    identities.map((entry) => [
      entry.platform_user_id,
      { userId: entry.user_id, displayName: entry.display_name, role: entry.role },
    ]),
  );
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const chatProvider = (env.CHAT_PROVIDER ?? 'memory') as ChatProvider;
  const llmProvider = (env.LLM_PROVIDER ?? 'scripted') as LlmProvider;
  const identities = parseIdentities(env.APPROVAL_IDENTITIES);

  return {
    port: readInt(env.PORT, 3000),
    store: env.DATABASE_URL ? 'postgres' : 'memory',
    databaseUrl: env.DATABASE_URL ?? null,
    llm: {
      provider: llmProvider,
      apiKey: env.ANTHROPIC_API_KEY ?? null,
      model: env.LLM_MODEL ?? 'claude-sonnet-4-6',
    },
    chat: {
      provider: chatProvider,
      slack: {
        botToken: env.SLACK_BOT_TOKEN ?? null,
        signingSecret: env.SLACK_SIGNING_SECRET ?? null,
        approvalChannel: env.SLACK_APPROVAL_CHANNEL ?? '#virtus-approvals',
      },
    },
    identities: identities.identities,
    identitiesError: identities.error,
    adminBaseUrl: env.ADMIN_BASE_URL ?? 'http://localhost:3000',
    approval: {
      ttlHours: readInt(env.APPROVAL_TTL_HOURS, 24),
    },
    knowledge: {
      staleAfterDays: readInt(env.SOURCE_STALE_AFTER_DAYS, 180),
    },
  };
}

/**
 * 起動前の設定検証。
 * 選択したチャット・LLM に必要な秘密情報が無ければ、黙って劣化させずに落とす。
 */
export function validateConfig(config: AppConfig): string[] {
  const problems: string[] = [];

  if (config.llm.provider === 'anthropic' && !config.llm.apiKey) {
    problems.push('LLM_PROVIDER=anthropic だが ANTHROPIC_API_KEY が未設定');
  }
  if (config.identitiesError) problems.push(config.identitiesError);

  if (config.chat.provider === 'slack') {
    if (!config.chat.slack.botToken) problems.push('CHAT_PROVIDER=slack だが SLACK_BOT_TOKEN が未設定');
    if (!config.chat.slack.signingSecret) {
      problems.push('CHAT_PROVIDER=slack だが SLACK_SIGNING_SECRET が未設定(FR-034 の署名検証に必須)');
    }
    // 承認者が 1 人も登録されていなければ、誰も Yellow/Red を承認できない。
    // 黙って起動すると案件が awaiting_approval のまま滞留するため、ここで落とす。
    if (!config.identities.some((entry) => entry.role === 'approver')) {
      problems.push(
        'CHAT_PROVIDER=slack だが APPROVAL_IDENTITIES に role=approver の利用者がいない' +
          '(FR-032 の最終確定はこの表のロールだけで判定するため、承認者が必要)',
      );
    }
  }
  if (config.chat.provider === 'teams') {
    problems.push('Teams は MVP で未実装です(FR-030: Slack か Teams の一方のみ)');
  }

  return problems;
}
