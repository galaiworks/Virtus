/**
 * エージェント共通の土台。
 *
 * 入力ハッシュ、実行時刻、LLM 異常応答の状態への写像を一箇所に集める。
 */

import { createHash } from 'node:crypto';
import type { LlmAdapter, LlmResult } from '../ports/llm.js';
import type { IdGenerator } from '../domain/ids.js';
import type { Clock } from '../domain/clock.js';
import type { CaseState } from '../domain/states.js';
import type { QaFinding } from '../domain/schemas.js';

export type AgentRole = 'supervisor' | 'knowledge' | 'improvement' | 'qa';

export interface AgentContext {
  llm: LlmAdapter;
  ids: IdGenerator;
  clock: Clock;
}

export interface AgentResult<T> {
  role: AgentRole;
  /** 出力契約の版数。回帰テストの差分管理に使う。 */
  schemaVersion: string;
  state: CaseState;
  /** 停止した場合は null。 */
  output: T | null;
  error: string | null;
  inputHash: string;
  startedAt: string;
  finishedAt: string;
  /** 停止・差戻しの理由。QA と監査へ引き継ぐ。 */
  findings: QaFinding[];
}

export abstract class BaseAgent<TInput, TOutput> {
  abstract readonly role: AgentRole;
  abstract readonly schemaVersion: string;

  constructor(protected readonly ctx: AgentContext) {}

  abstract execute(input: TInput): Promise<AgentResult<TOutput>>;

  protected hashInput(input: unknown): string {
    return createHash('sha256').update(JSON.stringify(input) ?? '').digest('hex').slice(0, 32);
  }

  protected result(args: {
    state: CaseState;
    output: TOutput | null;
    inputHash: string;
    startedAt: string;
    error?: string | null;
    findings?: QaFinding[];
  }): AgentResult<TOutput> {
    return {
      role: this.role,
      schemaVersion: this.schemaVersion,
      state: args.state,
      output: args.output,
      error: args.error ?? null,
      inputHash: args.inputHash,
      startedAt: args.startedAt,
      finishedAt: this.ctx.clock.now().toISOString(),
      findings: args.findings ?? [],
    };
  }

  /**
   * LLM の異常応答を状態へ写像する。
   *
   * - refusal        : モデルが応答を拒否した。自動ループでは解けないため人間レビューへ。
   * - incomplete     : 打ち切り。出力契約違反として自動差戻しの対象にする。
   * - schema_violation: 同上。
   * - transport_error: 基盤障害。AI オペレーション責任者が再試行可否を判断する。
   */
  protected mapLlmFailure(
    failure: Exclude<LlmResult<unknown>, { status: 'ok' }>,
  ): { state: CaseState; finding: QaFinding } {
    switch (failure.status) {
      case 'refusal':
        return {
          state: 'human_review_required',
          finding: {
            category: 'revision',
            root_cause: 'llm_refusal',
            severity: 'blocker',
            detail: `LLM が応答を拒否した: ${failure.reason}`,
            target: null,
          },
        };
      case 'incomplete':
      case 'schema_violation':
        return {
          state: 'needs_revision',
          finding: {
            category: 'revision',
            root_cause: 'llm_output_contract',
            severity: 'major',
            detail: `LLM の出力が契約を満たさなかった: ${failure.reason}`,
            target: null,
          },
        };
      case 'transport_error':
        return {
          state: 'execution_failed',
          finding: {
            category: 'execution',
            root_cause: 'llm_transport',
            severity: 'blocker',
            detail: `LLM 呼び出しに失敗した: ${failure.reason}`,
            target: null,
          },
        };
    }
  }
}
