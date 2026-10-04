/**
 * ユニット: JSON Schema、状態遷移、リスク分類、期限、ロール、scope 検証(手順書 E-1)。
 */

import { describe, expect, it } from 'vitest';
import {
  STATE_DEFINITIONS,
  allowsExecution,
  requiresExplicitHumanRestart,
  stateDefinition,
  strongestState,
  CASE_STATES,
} from '../../src/domain/states.js';
import {
  OPERATIONS,
  highestRisk,
  isGreenAutoExecutable,
  operationSpec,
} from '../../src/domain/risk.js';
import { validateApprovalPacket } from '../../src/domain/schemas.js';
import { narrowScope } from '../../src/approval/approval-service.js';
import type { ApprovalPacket } from '../../src/domain/schemas.js';

describe('状態機械(FR-020 / FR-021)', () => {
  it('9 状態すべてに介入者・停止範囲・再開地点が定義されている', () => {
    for (const state of CASE_STATES) {
      const def = stateDefinition(state);
      expect(def.systemAction.length).toBeGreaterThan(0);
      expect(def.resumeAt.length).toBeGreaterThan(0);
      expect(def.halts).toBeDefined();
      if (state !== 'pass') {
        expect(def.interveners.length).toBeGreaterThan(0);
      }
    }
    expect(Object.keys(STATE_DEFINITIONS)).toHaveLength(CASE_STATES.length);
  });

  it('FR-021 の優先順で最も強い状態を採る', () => {
    // security/incident > authorization > fact conflict > approval > clarification > revision > pass
    expect(strongestState(['pass', 'needs_revision'])).toBe('needs_revision');
    expect(strongestState(['needs_revision', 'needs_clarification'])).toBe('needs_clarification');
    expect(strongestState(['needs_clarification', 'awaiting_approval'])).toBe('awaiting_approval');
    expect(strongestState(['awaiting_approval', 'hold_for_decision'])).toBe('hold_for_decision');
    expect(strongestState(['hold_for_decision', 'blocked_authorization'])).toBe(
      'blocked_authorization',
    );
    expect(strongestState(['blocked_authorization', 'blocked_security'])).toBe('blocked_security');
    expect(strongestState(['blocked_security', 'incident_mode'])).toBe('incident_mode');
  });

  it('個人情報を含む対外行為は awaiting_approval ではなく blocked_security になる', () => {
    expect(strongestState(['awaiting_approval', 'blocked_security'])).toBe('blocked_security');
  });

  it('停止状態では実行キューが止まる', () => {
    expect(allowsExecution('pass')).toBe(true);
    for (const state of [
      'awaiting_approval',
      'blocked_authorization',
      'blocked_security',
      'hold_for_decision',
      'needs_clarification',
      'incident_mode',
      'human_review_required',
    ] as const) {
      expect(allowsExecution(state)).toBe(false);
    }
  });

  it('事故モードとセキュリティ停止は自律再開できない(FR-024)', () => {
    expect(requiresExplicitHumanRestart('incident_mode')).toBe(true);
    expect(requiresExplicitHumanRestart('blocked_security')).toBe(true);
    expect(requiresExplicitHumanRestart('needs_revision')).toBe(false);
  });
});

describe('リスク分類(FR-040)', () => {
  it('Green として自動実行できるのは可逆な社内操作だけ', () => {
    expect(isGreenAutoExecutable('internal_draft.save')).toBe(true);
    expect(isGreenAutoExecutable('task_draft.create')).toBe(true);
    expect(isGreenAutoExecutable('approval_request.post')).toBe(true);

    expect(isGreenAutoExecutable('external_email.send')).toBe(false);
    expect(isGreenAutoExecutable('crm.record.commit')).toBe(false);
    expect(isGreenAutoExecutable('storage.delete')).toBe(false);
    expect(isGreenAutoExecutable('storage.overwrite')).toBe(false);
    expect(isGreenAutoExecutable('contract.sign')).toBe(false);
  });

  it('Green の操作はすべて可逆で、ロールバック方法が定義されている', () => {
    for (const spec of Object.values(OPERATIONS)) {
      if (spec.risk === 'green') {
        expect(spec.reversible).toBe(true);
        expect(spec.autoExecutableInMvp).toBe(true);
      }
      expect(spec.rollback.length).toBeGreaterThan(0);
    }
  });

  it('MVP に含めない操作は自動実行対象外になっている(要件定義 §2)', () => {
    for (const id of [
      'external_email.send',
      'crm.record.commit',
      'storage.delete',
      'storage.overwrite',
    ] as const) {
      expect(operationSpec(id).autoExecutableInMvp).toBe(false);
    }
  });

  it('複数操作では最も強いリスクを採る', () => {
    expect(highestRisk(['internal_draft.save'])).toBe('green');
    expect(highestRisk(['internal_draft.save', 'external_email.send'])).toBe('yellow');
    expect(highestRisk(['internal_draft.save', 'external_email.send', 'contract.sign'])).toBe('red');
  });
});

const basePacket: ApprovalPacket = {
  request_id: 'req_1',
  case_id: 'case_1',
  operation: 'external_email.send',
  target: 'client@example.com',
  preview: '宛先: client@example.com',
  evidence: [{ claim_id: 'claim_1', summary: '進捗率は 72%' }],
  impact: 'リスク区分: YELLOW / 不可逆な操作',
  constraints: ['宛先は client@example.com のみ'],
  rollback: '送信は取り消せない',
  required_role: 'approver',
  expires_at: '2026-08-14T00:00:00.000Z',
  idempotency_key: 'idem_abc',
  risk: 'yellow',
  granted_scope: {
    operation: 'external_email.send',
    target: 'client@example.com',
    recipients: ['client@example.com'],
  },
  card_version: 1,
  nonce: 'nonce_1',
};

describe('承認パケットの必須項目(FR-023)', () => {
  it('全項目がそろっていれば通る', () => {
    const result = validateApprovalPacket(basePacket);
    expect(result.ok).toBe(true);
  });

  it.each([
    'rollback',
    'expires_at',
    'idempotency_key',
    'impact',
    'preview',
    'required_role',
  ] as const)('%s が欠けると実行キューに入らない', (field) => {
    const broken = { ...basePacket } as Record<string, unknown>;
    delete broken[field];
    const result = validateApprovalPacket(broken);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.missing).toContain(field);
  });

  it('制約が空でも弾く', () => {
    const result = validateApprovalPacket({ ...basePacket, constraints: [] });
    expect(result.ok).toBe(false);
  });
});

describe('条件付き承認の scope 検証(D-3 手順 5)', () => {
  const decision = (over: Partial<Parameters<typeof narrowScope>[1]> = {}) => ({
    decision: 'approved_with_conditions' as const,
    reason: '確認済み',
    conditions: [],
    scope_override: null,
    ...over,
  });

  it('宛先を絞り込む条件は許可される', () => {
    const packet = {
      ...basePacket,
      granted_scope: { ...basePacket.granted_scope, recipients: ['a@example.com', 'b@example.com'] },
    };
    const result = narrowScope(packet, decision({ scope_override: { recipients: ['a@example.com'] } }));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.scope.recipients).toEqual(['a@example.com']);
  });

  it('宛先を追加する条件は拒否される', () => {
    const result = narrowScope(
      basePacket,
      decision({ scope_override: { recipients: ['client@example.com', 'other@example.com'] } }),
    );
    expect(result.ok).toBe(false);
  });

  it('対象を変更する条件は拒否される', () => {
    const result = narrowScope(basePacket, decision({ scope_override: { target: 'other-target' } }));
    expect(result.ok).toBe(false);
  });

  it('条件文に scope 外の宛先が書かれていれば拒否される', () => {
    const result = narrowScope(
      basePacket,
      decision({ conditions: ['宛先に another@example.com も追加してください'] }),
    );
    expect(result.ok).toBe(false);
  });
});
