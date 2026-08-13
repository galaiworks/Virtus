/**
 * 監査イベントの記録(FR-042、非機能要件「監査性」)。
 *
 * すべての重要な状態遷移に、時刻・主体・入力参照・出力参照・判断・
 * 承認 ID・実行 ID を残す。detail には秘密情報と不要な個人情報を入れない。
 */

import type { StoreSession } from '../ports/store.js';
import type { AuditEvent, AuditEventType } from '../domain/types.js';
import type { ActorRole } from '../domain/states.js';
import type { IdGenerator } from '../domain/ids.js';
import type { Clock } from '../domain/clock.js';
import { redact } from '../security/redact.js';

export interface AuditInput {
  case_id: string;
  event_type: AuditEventType;
  actor: string;
  actor_role: ActorRole;
  input_refs?: readonly string[];
  output_refs?: readonly string[];
  decision?: string | null;
  approval_request_id?: string | null;
  execution_id?: string | null;
  detail?: Record<string, unknown>;
}

export class AuditRecorder {
  constructor(
    private readonly ids: IdGenerator,
    private readonly clock: Clock,
  ) {}

  async record(tx: StoreSession, input: AuditInput): Promise<AuditEvent> {
    const event: AuditEvent = {
      event_id: this.ids.next('evt'),
      case_id: input.case_id,
      event_type: input.event_type,
      actor: input.actor,
      actor_role: input.actor_role,
      occurred_at: this.clock.now().toISOString(),
      input_refs: input.input_refs ?? [],
      output_refs: input.output_refs ?? [],
      decision: input.decision ?? null,
      approval_request_id: input.approval_request_id ?? null,
      execution_id: input.execution_id ?? null,
      detail: sanitizeDetail(input.detail ?? {}),
    };
    await tx.insertAuditEvent(event);
    return event;
  }
}

/** ログへ落とす前に、文字列値から不要な個人情報・秘密情報を伏せる。 */
function sanitizeDetail(detail: Record<string, unknown>): Record<string, unknown> {
  const output: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(detail)) {
    output[key] = sanitizeValue(value);
  }
  return output;
}

function sanitizeValue(value: unknown): unknown {
  if (typeof value === 'string') return redact(value);
  if (Array.isArray(value)) return value.map((item) => sanitizeValue(item));
  if (value !== null && typeof value === 'object') {
    return sanitizeDetail(value as Record<string, unknown>);
  }
  return value;
}
