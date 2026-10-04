/**
 * 決定論 LLM アダプタ。
 *
 * 評価セット(20 件)と回帰テストを、提供元・モデル・気温に依存せず回すために使う。
 * 実提供元のアダプタと同じ `LlmAdapter` 契約を満たし、
 * `refusal` / `incomplete` / `schema_violation` を意図的に発生させられる。
 */

import type { LlmAdapter, LlmRequest, LlmResult } from '../../ports/llm.js';

/** 特定の役割・スキーマで異常応答を再現するための設定。 */
export interface ScriptedFailure {
  schemaName: string;
  result: 'refusal' | 'incomplete' | 'schema_violation' | 'transport_error';
  reason: string;
}

type Responder = (request: LlmRequest<unknown>) => unknown;

export class ScriptedLlmAdapter implements LlmAdapter {
  readonly name = 'scripted';

  private readonly responders: Map<string, Responder>;
  private readonly failures: ScriptedFailure[];
  /** 呼び出し履歴。テストでプロンプトの中身を検証するために保持する。 */
  readonly calls: { schemaName: string; role: string; system: string; userContent: string }[] = [];

  constructor(options?: { responders?: Record<string, Responder>; failures?: ScriptedFailure[] }) {
    this.responders = new Map(Object.entries({ ...defaultResponders, ...options?.responders }));
    this.failures = options?.failures ?? [];
  }

  async generateStructured<T>(request: LlmRequest<T>): Promise<LlmResult<T>> {
    this.calls.push({
      schemaName: request.schemaName,
      role: request.role,
      system: request.system,
      userContent: request.userContent,
    });

    const failure = this.failures.find((f) => f.schemaName === request.schemaName);
    if (failure) {
      if (failure.result === 'schema_violation') {
        return { status: 'schema_violation', reason: failure.reason, raw: '{}' };
      }
      return { status: failure.result, reason: failure.reason };
    }

    const responder = this.responders.get(request.schemaName);
    if (!responder) {
      return {
        status: 'transport_error',
        reason: `決定論アダプタに ${request.schemaName} の応答が登録されていません`,
      };
    }

    const candidate = responder(request as LlmRequest<unknown>);
    const parsed = request.schema.safeParse(candidate);
    if (!parsed.success) {
      return {
        status: 'schema_violation',
        reason: parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
        raw: JSON.stringify(candidate),
      };
    }
    return { status: 'ok', data: parsed.data, raw: JSON.stringify(candidate) };
  }
}

const str = (value: unknown, fallback = ''): string =>
  typeof value === 'string' && value.trim().length > 0 ? value : fallback;

const strArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];

/**
 * 既定の応答。`context` に入れた構造化データから機械的に文章を組み立てる。
 * 文章生成の巧拙は評価対象外であり、ここで検証するのは配管と統制である。
 */
const defaultResponders: Record<string, Responder> = {
  supervisor_prose: (request) => {
    const ctx = request.context ?? {};
    return {
      objective: str(ctx.objective, '目的未設定'),
      kpi: strArray(ctx.kpi).length > 0 ? strArray(ctx.kpi) : ['作成時間の短縮'],
      in_scope: strArray(ctx.desired_artifacts),
      out_of_scope: ['外部メールの自動送信', 'CRM の確定更新', '資料の削除・上書き'],
      risk_notes: strArray(ctx.risk_notes),
    };
  },

  knowledge_prose: (request) => {
    const ctx = request.context ?? {};
    const limitations = strArray(ctx.limitations);
    return {
      limitations:
        limitations.length > 0
          ? limitations
          : ['許可済み資料の範囲内のみを参照した。外部情報は根拠に含めていない。'],
    };
  },

  improvement_prose: (request) => {
    const ctx = request.context ?? {};
    const factTexts = strArray(ctx.fact_line_texts);
    const emailRequested = ctx.email_requested === true;
    const recipients = strArray(ctx.email_recipients);
    return {
      title: str(ctx.title, '週次報告(下書き)'),
      fact_line_texts: factTexts,
      proposals: strArray(ctx.proposals),
      email: emailRequested
        ? {
            subject: str(ctx.email_subject, '進捗のご報告'),
            body: [
              'お世話になっております。',
              '',
              ...factTexts.map((line) => `・${line}`),
              '',
              '不足している点がありましたらご指摘ください。',
              recipients.length > 0 ? `(宛先: ${recipients.join(', ')})` : '',
            ]
              .filter((line) => line !== '')
              .join('\n'),
          }
        : null,
    };
  },

  qa_prose: () => ({ additional_findings: [] }),
};
