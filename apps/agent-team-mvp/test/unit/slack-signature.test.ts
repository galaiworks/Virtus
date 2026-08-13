/**
 * ユニット: Slack の署名・タイムスタンプ検証(FR-034)。
 *
 * 正規のリクエストでない操作は拒否され、実行されないこと。
 */

import { createHmac } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { verifySlackSignature } from '../../src/adapters/chat/slack-adapter.js';

const SECRET = 'test-signing-secret';
const NOW = 1_786_000_000;

function sign(rawBody: string, timestamp: number, secret = SECRET): string {
  return `v0=${createHmac('sha256', secret).update(`v0:${timestamp}:${rawBody}`).digest('hex')}`;
}

describe('Slack 署名検証', () => {
  const rawBody = 'payload=%7B%22type%22%3A%22block_actions%22%7D';

  it('正規のリクエストを受け入れる', () => {
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: String(NOW),
      signature: sign(rawBody, NOW),
      rawBody,
      nowUnixSeconds: NOW,
    });
    expect(verdict.valid).toBe(true);
  });

  it('ボディが改ざんされた署名を拒否する', () => {
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: String(NOW),
      signature: sign(rawBody, NOW),
      rawBody: `${rawBody}&injected=1`,
      nowUnixSeconds: NOW,
    });
    expect(verdict).toEqual({ valid: false, reason: 'signature_mismatch' });
  });

  it('別のシークレットで署名されたリクエストを拒否する', () => {
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: String(NOW),
      signature: sign(rawBody, NOW, 'other-secret'),
      rawBody,
      nowUnixSeconds: NOW,
    });
    expect(verdict).toEqual({ valid: false, reason: 'signature_mismatch' });
  });

  it('古いタイムスタンプをリプレイとして拒否する', () => {
    const stale = NOW - 60 * 10;
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: String(stale),
      signature: sign(rawBody, stale),
      rawBody,
      nowUnixSeconds: NOW,
    });
    expect(verdict).toEqual({ valid: false, reason: 'stale_timestamp' });
  });

  it('未来方向のずれも拒否する', () => {
    const future = NOW + 60 * 10;
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: String(future),
      signature: sign(rawBody, future),
      rawBody,
      nowUnixSeconds: NOW,
    });
    expect(verdict).toEqual({ valid: false, reason: 'stale_timestamp' });
  });

  it('タイムスタンプが数値でなければ拒否する', () => {
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: 'not-a-number',
      signature: sign(rawBody, NOW),
      rawBody,
      nowUnixSeconds: NOW,
    });
    expect(verdict).toEqual({ valid: false, reason: 'bad_timestamp' });
  });

  it('署名が空でも例外にせず拒否する', () => {
    const verdict = verifySlackSignature({
      signingSecret: SECRET,
      timestamp: String(NOW),
      signature: '',
      rawBody,
      nowUnixSeconds: NOW,
    });
    expect(verdict.valid).toBe(false);
  });
});

export { sign as signSlackRequest };
