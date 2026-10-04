/**
 * LLM のポート(要件定義 §8、手順書 C-1)。
 *
 * Structured Outputs を使う場合でも、拒否や不完全出力は起こり得る。
 * よってアダプタは必ず判別可能な結果型を返し、アプリ側で受け取り・停止・再試行を行う。
 */

import type { z } from 'zod';

export interface LlmRequest<T> {
  /** 呼び出し元のエージェント役割。ログとプロンプト分離に使う。 */
  role: 'supervisor' | 'knowledge' | 'improvement' | 'qa';
  system: string;
  /** 資料本文などのデータ。指示として解釈させない(FR-014)。 */
  userContent: string;
  schemaName: string;
  schema: z.ZodType<T>;
  maxTokens?: number;
  /**
   * 決定論アダプタ(評価セット・テスト)が参照する構造化された入力。
   * 実提供元のアダプタは userContent だけを送り、ここは使わない。
   */
  context?: Record<string, unknown>;
}

export type LlmResult<T> =
  | { status: 'ok'; data: T; raw: string }
  | { status: 'refusal'; reason: string }
  | { status: 'incomplete'; reason: string }
  | { status: 'schema_violation'; reason: string; raw: string }
  | { status: 'transport_error'; reason: string };

export interface LlmAdapter {
  readonly name: string;
  generateStructured<T>(request: LlmRequest<T>): Promise<LlmResult<T>>;
}
