/**
 * 時刻の抽象化。
 *
 * 承認期限(FR-023)、Slack のタイムスタンプ検証(FR-034)、監査イベントの時刻は
 * すべてこの Clock を経由する。テストでは固定時刻を注入する。
 */

export interface Clock {
  now(): Date;
  /** Unix 秒。Slack の署名検証で使う。 */
  unixSeconds(): number;
}

export class SystemClock implements Clock {
  now(): Date {
    return new Date();
  }

  unixSeconds(): number {
    return Math.floor(Date.now() / 1000);
  }
}

/** テスト用。明示的に時刻を進める。 */
export class FixedClock implements Clock {
  constructor(private current: Date) {}

  now(): Date {
    return new Date(this.current.getTime());
  }

  unixSeconds(): number {
    return Math.floor(this.current.getTime() / 1000);
  }

  advance(ms: number): void {
    this.current = new Date(this.current.getTime() + ms);
  }

  set(next: Date): void {
    this.current = next;
  }
}
