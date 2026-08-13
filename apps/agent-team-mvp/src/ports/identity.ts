/**
 * 本人・ロールの解決(手順書 D-3 手順 2)。
 *
 * チャットプラットフォームの利用者 ID を、内部の本人とロールへ対応づける。
 * カードのボタンが返す値ではなく、必ずこの解決結果でロールを判定する。
 */

import type { ActorRole } from '../domain/states.js';

export interface InternalIdentity {
  userId: string;
  displayName: string;
  role: ActorRole;
}

export interface IdentityResolver {
  resolve(platformUserId: string): Promise<InternalIdentity | null>;
}

/** 設定表から解決する実装。MVP は少人数のため静的表で足りる。 */
export class StaticIdentityResolver implements IdentityResolver {
  constructor(private readonly table: Readonly<Record<string, InternalIdentity>>) {}

  async resolve(platformUserId: string): Promise<InternalIdentity | null> {
    return this.table[platformUserId] ?? null;
  }
}
