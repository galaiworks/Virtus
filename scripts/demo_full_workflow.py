#!/usr/bin/env python3
"""
Virtus Demo: 統合ワークフロー

サミット用デモスクリプト。
8体エージェントが連携して動く様子を実演。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import VirtusOrchestrator
from src.utils.config import Config


SAMPLE_BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
        "founder": "ガライ",
        "business": "AI 開発、SaaS、コンテンツ自動化",
        "target_audience": "ひとり社長・コーチ・コンサル・専門家",
        "unique_value_proposition": "海外最先端の AI エージェント技術を、日本のひとり社長が使えるレベルまで落とし込む",
    },
    "voice": {
        "tone": "プロフェッショナル × 親近感 × 直球",
        "personality": [
            "率直、嘘や曖昧さを嫌う",
            "海外動向に詳しい",
            "数字に強い",
            "実装力を見せる",
        ],
        "preferred": [
            "率直に言うと",
            "正直に言います",
            "本質は",
            "結論から言うと",
            "具体的には",
        ],
    },
    "content_strategy": {
        "pillar_topics": [
            "AI エージェント・マルチエージェント設計",
            "ひとり社長の自動化戦略",
            "海外最先端の AI 動向",
        ],
    },
    "forbidden": [
        "絶対",
        "必ず",
        "100%",
        "簡単に",
        "誰でも稼げる",
        "魔法のような",
    ],
}


def print_section(title: str):
    """セクションヘッダーを表示"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def print_result(name: str, result):
    """結果を表示"""
    status = "✅ 成功" if result.success else "❌ 失敗"
    print(f"  {name}: {status}")
    if not result.success and result.error:
        print(f"    エラー: {result.error}")


def demo_full_workflow():
    """統合ワークフローデモ"""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║   Virtus - 8体AIエージェントチーム デモンストレーション    ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ エラー: ANTHROPIC_API_KEY が設定されていません")
        print()
        print("設定方法:")
        print("  export ANTHROPIC_API_KEY=your_key_here")
        print()
        return

    print_section("1. Virtus オーケストレーター初期化")

    print("  8体のエージェントを初期化中...")
    print()
    print("  ┌─────────────────────────────────────────┐")
    print("  │ Lead Strategist (Opus 4.7)   - 戦略統括 │")
    print("  │ Researcher (Sonnet 4.6)      - 探索     │")
    print("  │ Drafter (Sonnet 4.6)         - 執筆     │")
    print("  │ Designer (Sonnet 4.6)        - デザイン │")
    print("  │ Distributor (Haiku 4.5)      - 配信     │")
    print("  │ Connector (Sonnet 4.6)       - 関係構築 │")
    print("  │ Analyst (Sonnet 4.6)         - 分析     │")
    print("  │ Guardian (Opus 4.7)          - 品質保証 │")
    print("  └─────────────────────────────────────────┘")
    print()

    config = Config(
        api_key=api_key,
        customer_id="demo",
        brain_path=Path("brain"),
    )

    try:
        orchestrator = VirtusOrchestrator(config, SAMPLE_BRAND_DNA)
        print("  ✅ 初期化完了")
    except Exception as e:
        print(f"  ❌ 初期化失敗: {e}")
        return

    print_section("2. 朝のワークフロー実行")

    print("  【05:00】Researcher: 情報収集開始")
    print("  【07:00】Lead Strategist: 朝報生成")
    print()

    try:
        result = orchestrator.run_morning_workflow()
        print(f"  ワークフロー結果: {'✅ 成功' if result.success else '⚠️ 部分的に完了'}")

        if "morning_brief" in result.results:
            brief_result = result.results["morning_brief"]
            if brief_result.success:
                print()
                print("  ┌─ 朝報プレビュー ──────────────────────┐")
                preview = brief_result.content[:500] if brief_result.content else ""
                for line in preview.split("\n")[:10]:
                    print(f"  │ {line[:50]}")
                print("  │ ...")
                print("  └────────────────────────────────────────┘")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

    print_section("3. コンテンツ生成ワークフロー実行")

    print("  テーマ: AIエージェントでひとり社長の時間を取り戻す方法")
    print("  タイプ: X投稿")
    print()

    try:
        result = orchestrator.run_content_generation_workflow(
            content_type="x_post",
            topic="AIエージェントでひとり社長の時間を取り戻す方法",
            style="insight",
        )

        for name, agent_result in result.results.items():
            print_result(name, agent_result)

        if "draft" in result.results and result.results["draft"].success:
            content = result.results["draft"].content
            print()
            print("  ┌─ 生成されたコンテンツ ─────────────────┐")
            if content:
                for line in str(content)[:300].split("\n"):
                    print(f"  │ {line[:50]}")
            print("  └────────────────────────────────────────┘")

        if "quality" in result.results:
            quality = result.results["quality"]
            if quality.success and quality.content:
                status = quality.content.get("status", "unknown")
                score = quality.content.get("final_score", 0)
                print()
                print(f"  品質ループ: {status} (スコア: {score}/100)")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

    print_section("4. デモ完了")

    print("  Virtus は以下を自動化します:")
    print()
    print("  ✓ 毎朝の情報収集と朝報配信")
    print("  ✓ コンテンツの執筆・デザイン・品質チェック")
    print("  ✓ PRタイムズからのリード抽出")
    print("  ✓ DM/コメントへの返信ドラフト作成")
    print("  ✓ 配信スケジューリング")
    print("  ✓ パフォーマンス分析と勝ちパターン抽出")
    print()
    print("  「労働時間で売る」→「成果と仕組みで売る」")
    print()
    print("  詳細: https://github.com/galaiworks/Virtus")
    print()


if __name__ == "__main__":
    demo_full_workflow()
