/**
 * LLM に任せる範囲の契約(手順書 C-1)。
 *
 * 設計方針:根拠の突合、権限判定、リスク区分、状態決定は決定論のコードで行い、
 * LLM には「文章化」と「追加の指摘」だけを任せる。
 * こうしないと、根拠付与率(G2)や承認の要否(G3)そのものをテストで検証できない。
 */

import { z } from 'zod';
import { exceptionCategorySchema } from '../domain/schemas.js';

/** 統括エージェントが LLM に求める要約。 */
export const supervisorProseSchema = z.object({
  objective: z.string().min(1),
  kpi: z.array(z.string()),
  in_scope: z.array(z.string()),
  out_of_scope: z.array(z.string()),
  risk_notes: z.array(z.string()),
});
export type SupervisorProse = z.infer<typeof supervisorProseSchema>;

/** ナレッジ/データエージェントが LLM に求める限界の言語化。 */
export const knowledgeProseSchema = z.object({
  limitations: z.array(z.string()),
});
export type KnowledgeProse = z.infer<typeof knowledgeProseSchema>;

/** 業務改善エージェントが LLM に求める本文。事実行の「文言」だけを扱う。 */
export const improvementProseSchema = z.object({
  title: z.string().min(1),
  /** 事実行の文言。根拠 ID の割当てはコード側で行う。 */
  fact_line_texts: z.array(z.string()),
  proposals: z.array(z.string()),
  email: z
    .object({
      subject: z.string().min(1),
      body: z.string().min(1),
    })
    .nullable(),
});
export type ImprovementProse = z.infer<typeof improvementProseSchema>;

/**
 * 品質/承認エージェントが LLM に求める追加指摘。
 * LLM は指摘を「増やす」ことしかできない。承認・リスク受容はさせない(FR-013)。
 */
export const qaProseSchema = z.object({
  additional_findings: z.array(
    z.object({
      category: exceptionCategorySchema,
      root_cause: z.string().min(1),
      severity: z.enum(['blocker', 'major', 'minor']),
      detail: z.string().min(1),
    }),
  ),
});
export type QaProse = z.infer<typeof qaProseSchema>;
