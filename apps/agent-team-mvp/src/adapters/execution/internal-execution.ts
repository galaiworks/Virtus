/**
 * 社内向けの限定実行アダプタ(FR-040)。
 *
 * MVP が自動実行してよいのは、社内下書きの保存・タスク下書きの作成・
 * 承認依頼の投稿だけ。いずれも可逆で、ロールバック参照を返す。
 */

import type { ExecutionAdapter, ExecutionCommand, ExecutionOutcome } from '../../ports/execution.js';
import { operationSpec, type OperationId } from '../../domain/risk.js';

export interface StoredDraft {
  key: string;
  operation: OperationId;
  target: string;
  version: number;
  payload: Record<string, unknown>;
  savedAt: string;
}

/**
 * 社内保存先のスタブ。
 * Phase 1 では実際の保存先(社内 Wiki・タスク管理)へ差し替える前提で、
 * 版管理とロールバック参照の形だけを先に固定している。
 */
export class InternalExecutionAdapter implements ExecutionAdapter {
  readonly name = 'internal';

  private readonly SUPPORTED: readonly OperationId[] = [
    'internal_draft.save',
    'task_draft.create',
    'approval_request.post',
  ];

  private readonly storage = new Map<string, StoredDraft[]>();

  constructor(private readonly now: () => Date = () => new Date()) {}

  supports(operation: OperationId): boolean {
    return this.SUPPORTED.includes(operation);
  }

  async execute(command: ExecutionCommand): Promise<ExecutionOutcome> {
    const spec = operationSpec(command.operation);
    if (!this.supports(command.operation)) {
      return {
        status: 'failed',
        error: `このアダプタは ${command.operation} を扱わない`,
        retryable: false,
      };
    }

    const key = `${command.case_id}::${command.operation}::${command.target}`;
    const versions = this.storage.get(key) ?? [];
    const version = versions.length + 1;
    const record: StoredDraft = {
      key,
      operation: command.operation,
      target: command.target,
      version,
      payload: command.payload,
      savedAt: this.now().toISOString(),
    };
    versions.push(record);
    this.storage.set(key, versions);

    return {
      status: 'succeeded',
      result: `${spec.label}を保存した(版 ${version})`,
      rollbackRef: version > 1 ? `${key}#v${version - 1}` : `${key}#delete`,
    };
  }

  /** 監査・テスト用。保存された下書きを取り出す。 */
  list(caseId: string): StoredDraft[] {
    return [...this.storage.values()].flat().filter((d) => d.key.startsWith(`${caseId}::`));
  }
}

/**
 * MVP が自動実行しない操作の受け皿。
 *
 * 外部メール送信・CRM 確定更新・削除・上書き等は、承認されても
 * ここで人間実行へ引き渡す(要件定義 §2「MVP に含めない」)。
 */
export class ManualHandoffAdapter implements ExecutionAdapter {
  readonly name = 'manual_handoff';

  supports(operation: OperationId): boolean {
    return !operationSpec(operation).autoExecutableInMvp;
  }

  async execute(command: ExecutionCommand): Promise<ExecutionOutcome> {
    const spec = operationSpec(command.operation);
    return {
      status: 'handed_off_to_human',
      result: `${spec.label}は MVP の自動実行対象外。承認記録を添えて人間実行へ引き渡した(対象: ${command.target})`,
    };
  }
}
