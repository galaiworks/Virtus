/**
 * 識別子の採番。
 *
 * 監査要件(FR-042)より、すべての実体は接頭辞付きの ID を持ち、
 * `case_id` から根拠・承認・実行・監査イベントをたどれる。
 * テストと評価セットを決定論的に回すため、採番は差し替え可能にする。
 */

import { randomUUID } from 'node:crypto';

export type IdPrefix =
  | 'case'
  | 'src'
  | 'claim'
  | 'run'
  | 'art'
  | 'req'
  | 'dec'
  | 'job'
  | 'evt'
  | 'nonce';

export interface IdGenerator {
  next(prefix: IdPrefix): string;
}

/** 本番用。UUID v4 を接頭辞付きで返す。 */
export class RandomIdGenerator implements IdGenerator {
  next(prefix: IdPrefix): string {
    return `${prefix}_${randomUUID().replaceAll('-', '')}`;
  }
}

/** テスト・評価用。接頭辞ごとの連番を返す。 */
export class SequentialIdGenerator implements IdGenerator {
  private readonly counters = new Map<IdPrefix, number>();

  next(prefix: IdPrefix): string {
    const n = (this.counters.get(prefix) ?? 0) + 1;
    this.counters.set(prefix, n);
    return `${prefix}_${String(n).padStart(4, '0')}`;
  }
}
