/**
 * 依存の組み立て(composition root)。
 *
 * 非機能要件「保守性」より、エージェント・LLM・チャット・実行先・保存先は
 * すべてアダプタとして差し替えられる。ここが唯一それらを結線する場所。
 */

import type { AppConfig } from './config.js';
import { loadConfig } from './config.js';
import { RandomIdGenerator, SequentialIdGenerator, type IdGenerator } from './domain/ids.js';
import { SystemClock, type Clock } from './domain/clock.js';
import type { Store } from './ports/store.js';
import type { LlmAdapter } from './ports/llm.js';
import type { ChatAdapter } from './ports/chat.js';
import type { IdentityResolver } from './ports/identity.js';
import { StaticIdentityResolver } from './ports/identity.js';
import { MemoryStore } from './adapters/store/memory-store.js';
import { PgStore } from './adapters/store/pg-store.js';
import { ScriptedLlmAdapter } from './adapters/llm/scripted-llm.js';
import { AnthropicLlmAdapter } from './adapters/llm/anthropic-llm.js';
import { MemoryChatAdapter, UnimplementedChatAdapter } from './adapters/chat/memory-chat.js';
import { HttpSlackClient, SlackChatAdapter } from './adapters/chat/slack-adapter.js';
import {
  InternalExecutionAdapter,
  ManualHandoffAdapter,
} from './adapters/execution/internal-execution.js';
import { AuditRecorder } from './audit/audit-log.js';
import { SupervisorAgent } from './agents/supervisor-agent.js';
import { KnowledgeAgent } from './agents/knowledge-agent.js';
import { ImprovementAgent } from './agents/improvement-agent.js';
import { QaAgent } from './agents/qa-agent.js';
import { ApprovalPacketBuilder } from './approval/packet.js';
import { ApprovalService } from './approval/approval-service.js';
import { ExecutionRunner } from './execution/execution-runner.js';
import { Orchestrator } from './workflow/pipeline.js';

export interface App {
  config: AppConfig;
  store: Store;
  llm: LlmAdapter;
  chat: ChatAdapter;
  identities: IdentityResolver;
  ids: IdGenerator;
  clock: Clock;
  audit: AuditRecorder;
  internalExecution: InternalExecutionAdapter;
  orchestrator: Orchestrator;
  approvals: ApprovalService;
  close(): Promise<void>;
}

export interface BuildAppOverrides {
  config?: Partial<AppConfig>;
  store?: Store;
  llm?: LlmAdapter;
  chat?: ChatAdapter;
  identities?: IdentityResolver;
  ids?: IdGenerator;
  clock?: Clock;
}

/** 既定の本人・ロール表。実運用では IdP または設定ファイルから読む。 */
const DEFAULT_IDENTITIES = {
  U_APPROVER: { userId: 'approver-1', displayName: '承認権者', role: 'approver' as const },
  U_OWNER: { userId: 'owner-1', displayName: 'プロセスオーナー', role: 'process_owner' as const },
  U_REQUESTER: { userId: 'requester-1', displayName: '依頼者', role: 'requester' as const },
};

export function buildApp(overrides: BuildAppOverrides = {}): App {
  const config: AppConfig = { ...loadConfig(), ...overrides.config } as AppConfig;

  const clock = overrides.clock ?? new SystemClock();
  const ids = overrides.ids ?? new RandomIdGenerator();

  const store =
    overrides.store ??
    (config.store === 'postgres' && config.databaseUrl
      ? new PgStore(config.databaseUrl)
      : new MemoryStore());

  const llm =
    overrides.llm ??
    (config.llm.provider === 'anthropic' && config.llm.apiKey
      ? new AnthropicLlmAdapter({ apiKey: config.llm.apiKey, model: config.llm.model })
      : new ScriptedLlmAdapter());

  const chat = overrides.chat ?? buildChatAdapter(config);
  const identities = overrides.identities ?? new StaticIdentityResolver(DEFAULT_IDENTITIES);

  const audit = new AuditRecorder(ids, clock);
  const agentCtx = { llm, ids, clock };

  const internalExecution = new InternalExecutionAdapter(() => clock.now());
  const executor = new ExecutionRunner(
    [internalExecution, new ManualHandoffAdapter()],
    ids,
    clock,
    audit,
  );

  const packetBuilder = new ApprovalPacketBuilder(ids, clock, {
    ttlHours: config.approval.ttlHours,
  });

  // ApprovalService と Orchestrator は相互に依存する。
  // 承認後の再開は Orchestrator が持つため、遅延参照で結線する。
  let orchestrator!: Orchestrator;
  const approvals = new ApprovalService({
    store,
    chat,
    identities,
    audit,
    ids,
    clock,
    approvalChannel: config.chat.slack.approvalChannel,
    resumeAfterApproval: (tx, args) => orchestrator.resumeAfterApproval(tx, args),
  });

  orchestrator = new Orchestrator({
    store,
    ids,
    clock,
    audit,
    supervisor: new SupervisorAgent(agentCtx),
    knowledge: new KnowledgeAgent(agentCtx, { staleAfterDays: config.knowledge.staleAfterDays }),
    improvement: new ImprovementAgent(agentCtx),
    qa: new QaAgent(agentCtx),
    packetBuilder,
    approvals,
    executor,
  });

  return {
    config,
    store,
    llm,
    chat,
    identities,
    ids,
    clock,
    audit,
    internalExecution,
    orchestrator,
    approvals,
    close: () => store.close(),
  };
}

function buildChatAdapter(config: AppConfig): ChatAdapter {
  switch (config.chat.provider) {
    case 'slack': {
      if (!config.chat.slack.botToken) {
        throw new Error('CHAT_PROVIDER=slack には SLACK_BOT_TOKEN が必要です');
      }
      return new SlackChatAdapter(
        new HttpSlackClient(config.chat.slack.botToken),
        config.adminBaseUrl,
      );
    }
    case 'teams':
      // FR-030: MVP は一方のみ。未選択側は明示的に未実装とする。
      return new UnimplementedChatAdapter('teams');
    case 'memory':
    default:
      return new MemoryChatAdapter();
  }
}

/**
 * テスト・評価セット向けの決定論的な組み立て。
 * 保存先・LLM・チャットをすべてインメモリの実装に固定し、外部通信を行わない。
 */
export function buildDeterministicApp(overrides: BuildAppOverrides = {}): App {
  const deterministicConfig: Partial<AppConfig> = {
    store: 'memory',
    databaseUrl: null,
    llm: { provider: 'scripted', apiKey: null, model: 'scripted' },
    chat: {
      provider: 'memory',
      slack: { botToken: null, signingSecret: null, approvalChannel: '#test-approvals' },
    },
  };

  return buildApp({
    ...overrides,
    ids: overrides.ids ?? new SequentialIdGenerator(),
    store: overrides.store ?? new MemoryStore(),
    llm: overrides.llm ?? new ScriptedLlmAdapter(),
    chat: overrides.chat ?? new MemoryChatAdapter(),
    config: { ...deterministicConfig, ...overrides.config },
  });
}
