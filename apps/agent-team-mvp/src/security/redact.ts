/**
 * チャットカード・監査ログ向けのマスキング。
 *
 * 非機能要件より、カードとログには秘密情報・不要な個人情報・実行トークンを載せない。
 */

import { scanForPii } from './pii.js';

/** 検出した個人情報・秘密情報を区分名に置き換える。 */
export function redact(text: string, permitted: readonly string[] = []): string {
  const findings = scanForPii(text, permitted).filter((f) => f.unnecessary);
  let output = text;
  // 長い一致から順に置換し、部分一致による崩れを避ける。
  for (const finding of [...findings].sort((a, b) => b.value.length - a.value.length)) {
    output = output.split(finding.value).join(`[マスク:${finding.kind}]`);
  }
  return output;
}

/** カード表示用に本文を要約する。原文全文はカードに載せない(D-2)。 */
export function previewExcerpt(text: string, maxChars = 280, permitted: readonly string[] = []): string {
  const masked = redact(text, permitted);
  const collapsed = masked.replaceAll(/\s+/g, ' ').trim();
  return collapsed.length <= maxChars ? collapsed : `${collapsed.slice(0, maxChars)}…(以下は詳細画面で確認)`;
}
