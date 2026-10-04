/**
 * Anthropic 提供元アダプタ。
 *
 * 構造化出力はツール定義(input_schema)で強制する。
 * それでも拒否・打ち切り・スキーマ違反は起こり得るため、
 * 判別可能な結果型に落として呼び出し側へ返す(手順書 C-1)。
 */

import Anthropic from '@anthropic-ai/sdk';
import type { LlmAdapter, LlmRequest, LlmResult } from '../../ports/llm.js';
import { zodToJsonSchema } from './zod-to-json-schema.js';

export interface AnthropicLlmOptions {
  apiKey: string;
  model?: string;
  maxTokens?: number;
  /** 失敗時の再試行回数。ネットワーク由来の一時障害のみを対象にする。 */
  maxRetries?: number;
}

export class AnthropicLlmAdapter implements LlmAdapter {
  readonly name = 'anthropic';

  private readonly client: Anthropic;
  private readonly model: string;
  private readonly defaultMaxTokens: number;

  constructor(options: AnthropicLlmOptions) {
    this.client = new Anthropic({
      apiKey: options.apiKey,
      maxRetries: options.maxRetries ?? 2,
    });
    this.model = options.model ?? 'claude-sonnet-4-6';
    this.defaultMaxTokens = options.maxTokens ?? 4096;
  }

  async generateStructured<T>(request: LlmRequest<T>): Promise<LlmResult<T>> {
    const toolName = request.schemaName;
    let response: Anthropic.Messages.Message;

    try {
      response = await this.client.messages.create({
        model: this.model,
        max_tokens: request.maxTokens ?? this.defaultMaxTokens,
        system: request.system,
        tools: [
          {
            name: toolName,
            description: `${toolName} の構造化出力を返す。必ずこのツールだけを呼ぶこと。`,
            input_schema: zodToJsonSchema(request.schema) as Anthropic.Messages.Tool.InputSchema,
          },
        ],
        tool_choice: { type: 'tool', name: toolName },
        messages: [{ role: 'user', content: request.userContent }],
      });
    } catch (error) {
      return {
        status: 'transport_error',
        reason: error instanceof Error ? error.message : String(error),
      };
    }

    if (response.stop_reason === 'max_tokens') {
      return { status: 'incomplete', reason: '出力が max_tokens で打ち切られた' };
    }
    if (response.stop_reason === 'refusal') {
      return { status: 'refusal', reason: 'モデルが応答を拒否した' };
    }

    const toolUse = response.content.find(
      (block): block is Anthropic.Messages.ToolUseBlock =>
        block.type === 'tool_use' && block.name === toolName,
    );
    if (!toolUse) {
      const text = response.content
        .filter((block): block is Anthropic.Messages.TextBlock => block.type === 'text')
        .map((block) => block.text)
        .join('\n');
      return {
        status: 'incomplete',
        reason: `構造化出力が返らなかった(stop_reason=${response.stop_reason}): ${text.slice(0, 200)}`,
      };
    }

    const parsed = request.schema.safeParse(toolUse.input);
    if (!parsed.success) {
      return {
        status: 'schema_violation',
        reason: parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
        raw: JSON.stringify(toolUse.input),
      };
    }

    return { status: 'ok', data: parsed.data, raw: JSON.stringify(toolUse.input) };
  }
}
