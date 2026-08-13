/**
 * 自動差戻しの上限(FR-022)。
 *
 * 同一の例外カテゴリかつ同一根本原因の自動差戻しは 2 回まで。
 * 3 回目の検出で `human_review_required` へ移し、自動ループを止める。
 * 結果として 4 回目の自動差戻しは発生しない。
 */

import type { StoreSession } from '../ports/store.js';
import type { ExceptionCategory, QaFinding } from '../domain/schemas.js';

export const MAX_AUTO_REVISIONS = 2;

export interface RetryDecision {
  /** 自動差戻しを実施してよいか。 */
  allowAutoRevision: boolean;
  /** 上限に達した根本原因。 */
  exhausted: { category: ExceptionCategory; root_cause: string; auto_revisions: number } | null;
}

/**
 * 差戻し対象の指摘から、自動差戻しを続けてよいかを判定し、カウンタを進める。
 *
 * @param findings 今回の差戻しの原因となった指摘。
 */
export async function evaluateRetryBudget(
  tx: StoreSession,
  caseId: string,
  findings: readonly QaFinding[],
): Promise<RetryDecision> {
  if (findings.length === 0) {
    return { allowAutoRevision: false, exhausted: null };
  }

  // 「同一カテゴリかつ同一根本原因」は 1 件として数える。
  // 同じ原因で指摘が複数出ても、1 回の差戻しは 1 回として計上する。
  const causes = [
    ...new Map(
      findings.map((f) => [`${f.category}::${f.root_cause}`, f] as const),
    ).values(),
  ];

  // まず、いずれかの根本原因が上限に達しているかを確認する。
  for (const finding of causes) {
    const counter = await tx.getRetryCounter(caseId, finding.category, finding.root_cause);
    const done = counter?.auto_revisions ?? 0;
    if (done >= MAX_AUTO_REVISIONS) {
      return {
        allowAutoRevision: false,
        exhausted: {
          category: finding.category,
          root_cause: finding.root_cause,
          auto_revisions: done,
        },
      };
    }
  }

  // 上限未満のときだけカウンタを進め、自動差戻しを許可する。
  for (const finding of causes) {
    const counter = await tx.getRetryCounter(caseId, finding.category, finding.root_cause);
    await tx.upsertRetryCounter({
      case_id: caseId,
      category: finding.category,
      root_cause: finding.root_cause,
      auto_revisions: (counter?.auto_revisions ?? 0) + 1,
    });
  }

  return { allowAutoRevision: true, exhausted: null };
}
