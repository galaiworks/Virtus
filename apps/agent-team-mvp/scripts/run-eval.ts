/**
 * 評価セットの実行スクリプト。
 *
 *   npm run eval
 *
 * 変更のたびにこれを回し、結果差分を記録する(手順書 E-2 手順 3)。
 */

import { runEvalSuite } from '../src/eval/runner.js';
import { runHitlSuite } from '../src/eval/hitl-runner.js';

async function main(): Promise<void> {
  const suite = await runEvalSuite();
  const hitl = await runHitlSuite();

  console.log('\n=== 代表 20 件 評価セット ===');
  for (const result of suite.results) {
    const mark = result.passed ? 'PASS' : 'FAIL';
    console.log(
      `[${mark}] ${result.id} (${result.group}) ${result.title}\n` +
        `        状態=${result.observed.state} ` +
        `根拠付与率=${result.observed.evidenceCoverage === null ? '-' : result.observed.evidenceCoverage.toFixed(3)} ` +
        `差戻し=${result.observed.revisionRounds} ` +
        `実行=${result.observed.executedOperations.join(',') || 'なし'} ` +
        `承認要求=${result.observed.approvalRequests}`,
    );
    for (const failure of result.failures) console.log(`        └ ${failure}`);
  }

  console.log('\n=== HITL 5 件 ===');
  for (const result of hitl.results) {
    const mark = result.passed ? 'PASS' : 'FAIL';
    console.log(`[${mark}] ${result.id} ${result.title}`);
    for (const failure of result.failures) console.log(`        └ ${failure}`);
  }

  console.log(
    `\n合計: 評価セット ${suite.passed}/${suite.total} 合格 / HITL ${hitl.passed}/${hitl.total} 合格`,
  );

  if (suite.failed > 0 || hitl.failed > 0) {
    console.error('\nパイロット開始条件(F-1)を満たしていません。');
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
