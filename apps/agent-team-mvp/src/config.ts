/**
 * 環境設定。
 *
 * 非機能要件「セキュリティ」より、API キー・署名シークレット・アクセストークンは
 * サーバー側の環境変数からのみ読む。クライアント・カード・ログへ出さない。
 */

export type LlmProvider = 'anthropic' | 'scripted';
export type ChatProvider = 'slack' | 'teams' | 'memory';
export type StoreProvider = 'postgres' | 'memory';

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

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const chatProvider = (env.CHAT_PROVIDER ?? 'memory') as ChatProvider;
  const llmProvider = (env.LLM_PROVIDER ?? 'scripted') as LlmProvider;

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
  if (config.chat.provider === 'slack') {
    if (!config.chat.slack.botToken) problems.push('CHAT_PROVIDER=slack だが SLACK_BOT_TOKEN が未設定');
    if (!config.chat.slack.signingSecret) {
      problems.push('CHAT_PROVIDER=slack だが SLACK_SIGNING_SECRET が未設定(FR-034 の署名検証に必須)');
    }
  }
  if (config.chat.provider === 'teams') {
    problems.push('Teams は MVP で未実装です(FR-030: Slack か Teams の一方のみ)');
  }

  return problems;
}
