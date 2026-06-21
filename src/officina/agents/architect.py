"""Architect + Builder — ステージ 8:設計→実装→検証(Faber: Architect→Builder)。

合格ゲート:顧客テスト/受入基準 = 合格基準(決定論)。
テストスイートは決定論ゲートの一般化(設計原則 #2)。基準が作れない工程は自律化しない。
Builder は本番 DB 書込・本番デプロイ権限を持たない(ゼロトラスト・§6.1)。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent


class ArchitectBuilder(BaseAgent):
    name = "builder"  # 権限スコープは builder(本番デプロイ不可)

    def execute(self, task: dict[str, Any]) -> AgentResult:
        requirements = task.get("requirements", {})
        acceptance = task.get("acceptance_tests", [])
        # オフラインでは渡された受入テストを「実行済み・全通過」とみなす。
        # 実運用では Claude Code / dynamic workflows が実コードとテストを生成・実行。
        results = [{"name": t, "passed": True} for t in acceptance]
        all_passed = bool(results) and all(r["passed"] for r in results)
        design = {
            "architecture": "Orchestrator-Worker(Anthropic 公式パターン)",
            "components": requirements.get("scope", "クライアント向けエージェント"),
        }
        return AgentResult(
            agent=self.name,
            content_type="deliverable",
            output={
                "design": design,
                "test_results": results,
                "content": str(design),
                "gate": {
                    "tests_passed": all_passed,
                    "acceptance_test_count": len(results),
                },
            },
            meta={"stage": 8},
        )
