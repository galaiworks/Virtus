/**
 * ユニット: 環境設定の読み取りと起動前検証。
 *
 * 承認者が 1 人も登録されていないまま Slack を有効にすると、
 * 案件が awaiting_approval のまま誰にも承認されず滞留する。
 * そのため、黙って劣化させずに起動を止めることを確認する。
 */

import { describe, expect, it } from 'vitest';
import { loadConfig, parseIdentities, toIdentityTable, validateConfig } from '../../src/config.js';

const APPROVER = {
  platform_user_id: 'U01ABC2DEF',
  user_id: 'garai',
  display_name: 'ガライ',
  role: 'approver',
};

const slackEnv = (extra: Record<string, string> = {}): NodeJS.ProcessEnv => ({
  CHAT_PROVIDER: 'slack',
  SLACK_BOT_TOKEN: 'xoxb-test',
  SLACK_SIGNING_SECRET: 'secret',
  APPROVAL_IDENTITIES: JSON.stringify([APPROVER]),
  ...extra,
});

describe('APPROVAL_IDENTITIES の解析', () => {
  it('未設定なら空表を返し、エラーにはしない', () => {
    expect(parseIdentities(undefined)).toEqual({ identities: [], error: null });
    expect(parseIdentities('   ')).toEqual({ identities: [], error: null });
  });

  it('正しい JSON 配列を読む', () => {
    const result = parseIdentities(JSON.stringify([APPROVER]));
    expect(result.error).toBeNull();
    expect(result.identities).toHaveLength(1);
    expect(result.identities[0]?.role).toBe('approver');
  });

  it('壊れた JSON は黙って無視せずエラーにする', () => {
    const result = parseIdentities('{not json');
    expect(result.identities).toEqual([]);
    expect(result.error).toContain('JSON として解析できない');
  });

  it('未知のロールを拒否する', () => {
    const result = parseIdentities(JSON.stringify([{ ...APPROVER, role: 'superuser' }]));
    expect(result.identities).toEqual([]);
    expect(result.error).toContain('形式が不正');
  });

  it('必須項目が欠けていれば拒否する', () => {
    const result = parseIdentities(JSON.stringify([{ platform_user_id: 'U1' }]));
    expect(result.identities).toEqual([]);
    expect(result.error).toContain('形式が不正');
  });

  it('同じ利用者 ID が二重に登録されていれば拒否する', () => {
    const result = parseIdentities(
      JSON.stringify([APPROVER, { ...APPROVER, user_id: 'other', role: 'requester' }]),
    );
    expect(result.identities).toEqual([]);
    expect(result.error).toContain('重複した platform_user_id');
  });

  it('IdentityResolver が使う形へ変換する', () => {
    const table = toIdentityTable(parseIdentities(JSON.stringify([APPROVER])).identities);
    expect(table['U01ABC2DEF']).toEqual({
      userId: 'garai',
      displayName: 'ガライ',
      role: 'approver',
    });
  });
});

describe('起動前検証', () => {
  it('Slack の設定がそろっていれば通る', () => {
    expect(validateConfig(loadConfig(slackEnv()))).toEqual([]);
  });

  it('承認ロールの利用者がいなければ起動を止める', () => {
    const env = slackEnv({
      APPROVAL_IDENTITIES: JSON.stringify([{ ...APPROVER, role: 'requester' }]),
    });
    const problems = validateConfig(loadConfig(env));
    expect(problems.join('\n')).toContain('role=approver の利用者がいない');
  });

  it('APPROVAL_IDENTITIES 未設定のまま Slack を有効にしたら起動を止める', () => {
    const env = slackEnv();
    delete env.APPROVAL_IDENTITIES;
    const problems = validateConfig(loadConfig(env));
    expect(problems.join('\n')).toContain('role=approver の利用者がいない');
  });

  it('壊れた APPROVAL_IDENTITIES は起動時に報告される', () => {
    const problems = validateConfig(loadConfig(slackEnv({ APPROVAL_IDENTITIES: 'oops' })));
    expect(problems.join('\n')).toContain('JSON として解析できない');
  });

  it('署名シークレットが無ければ起動を止める(FR-034)', () => {
    const env = slackEnv();
    delete env.SLACK_SIGNING_SECRET;
    expect(validateConfig(loadConfig(env)).join('\n')).toContain('SLACK_SIGNING_SECRET');
  });

  it('Teams は未実装として落とす(FR-030)', () => {
    const problems = validateConfig(loadConfig({ CHAT_PROVIDER: 'teams' }));
    expect(problems.join('\n')).toContain('Teams は MVP で未実装');
  });

  it('チャットが memory なら承認者表は必須ではない', () => {
    expect(validateConfig(loadConfig({}))).toEqual([]);
  });

  it('LLM_PROVIDER=anthropic には API キーが要る', () => {
    const problems = validateConfig(loadConfig({ LLM_PROVIDER: 'anthropic' }));
    expect(problems.join('\n')).toContain('ANTHROPIC_API_KEY');
  });
});
