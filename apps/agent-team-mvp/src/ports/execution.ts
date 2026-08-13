/**
 * 実行先のポート(FR-040 / FR-041)。
 *
 * 実行アダプタは「許可された scope の操作だけ」を受け取る。
 * 承認の有無、リスク区分の判定、冪等性の確認は ExecutionRunner が先に行う。
 */

import type { OperationId } from '../domain/risk.js';

export interface ExecutionCommand {
  case_id: string;
  operation: OperationId;
  target: string;
  /** 実行内容。宛先・本文など。 */
  payload: Record<string, unknown>;
  idempotency_key: string;
}

export type ExecutionOutcome =
  | { status: 'succeeded'; result: string; rollbackRef: string | null }
  | { status: 'failed'; error: string; retryable: boolean }
  /** MVP では自動実行しない操作。承認済みでも人間実行へ引き渡す。 */
  | { status: 'handed_off_to_human'; result: string };

export interface ExecutionAdapter {
  readonly name: string;
  supports(operation: OperationId): boolean;
  execute(command: ExecutionCommand): Promise<ExecutionOutcome>;
}
