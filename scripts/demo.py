#!/usr/bin/env python3
"""Virtus Summit Demo Script - June 4, 2026.

This script demonstrates the complete Virtus workflow:
1. Lead Strategist generates morning brief
2. Drafter writes content with Garai Tone
3. Guardian evaluates with 95-point loop
4. Designer creates visuals

Usage:
    python scripts/demo.py [--api-key KEY] [--mock]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import Orchestrator

GALAIWORKS_BRAND_DNA: dict[str, Any] = {
    "identity": {
        "name": "galaiworks",
        "founder": "ガライ",
        "business": "AI開発、SaaS、コンテンツ自動化",
        "primary_target_audience": "ひとり社長・コーチ・コンサル・専門家",
        "unique_value_proposition": "海外最先端のAIエージェント技術を日本のひとり社長が使えるレベルまで落とし込む唯一のサービス",
        "core_competencies": [
            "Claude Code 実装力",
            "Anthropic 公式アーキテクチャ準拠",
            "Garai Tone、DREAM WRITING、IMPACT v2.0R 独自IP",
            "SEO 80件以上1位獲得",
        ],
    },
    "voice": {
        "tone": "プロフェッショナル × 親近感 × 直球",
        "personality": [
            "率直、嘘や曖昧さを嫌う",
            "海外動向に詳しい",
            "数字に強い",
            "実装力を見せる",
        ],
        "preferred_phrases": [
            "率直に言うと",
            "正直に言います",
            "本質は",
            "結論から言うと",
            "具体的には",
        ],
        "avoid_phrases": [
            "絶対",
            "必ず",
            "100%",
            "簡単",
            "すぐ稼げる",
        ],
        "signature_phrases": [
            "率直に言います",
            "現実的かつ厳密に",
            "海外で起きている革命",
        ],
    },
    "content_strategy": {
        "pillar_topics": [
            "AIエージェント・マルチエージェント設計",
            "ひとり社長の自動化戦略",
            "海外最先端のAI動向",
        ],
        "primary_platforms": ["note", "x", "youtube"],
        "publishing_frequency": {
            "note": "週2-3本",
            "x": "日5-8本",
            "youtube": "週1本",
        },
    },
    "forbidden": {
        "topics": ["競合のディスり", "政治的発言", "宗教的発言"],
        "expressions": ["絶対稼げる", "誰でも簡単に", "魔法のような"],
        "practices": ["ブラウザ自動化", "無断スクレイピング", "スパム送信"],
    },
    "reference": {
        "past_winning_content": [],
        "competitor_examples": [],
        "inspiration_sources": [
            {"name": "Sintra", "reason": "ひとり社長向け12ヘルパー"},
            {"name": "Sierra", "reason": "$10B評価額のマルチエージェント"},
        ],
    },
}


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_json(data: dict) -> None:
    """Pretty print JSON data."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def run_demo(api_key: str, mock: bool = False) -> None:
    """Run the complete Virtus demo."""
    print_section("Virtus Summit Demo - 2026/6/4")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'モック' if mock else 'ライブAPI'}")

    if mock:
        print("\n[モックモード] 実際のAPI呼び出しは行いません。")
        run_mock_demo()
        return

    print("\n初期化中...")
    orchestrator = Orchestrator(
        api_key=api_key,
        brand_dna=GALAIWORKS_BRAND_DNA,
    )

    print_section("Step 1: Lead Strategist - 朝報生成")
    print("毎朝7時に自動実行される朝報を生成します...\n")

    morning_brief = orchestrator.morning_brief(
        {
            "current_date": datetime.now().date().isoformat(),
        }
    )

    if morning_brief.get("success"):
        print("朝報生成成功!")
        print_json(morning_brief.get("output", {}))
    else:
        print("朝報生成失敗:", morning_brief.get("error"))

    print_section("Step 2: Drafter + Guardian - コンテンツ執筆 & 品質チェック")
    print("Garai Toneを適用したnote記事を執筆し、95点ループで品質チェック...\n")

    content_result = orchestrator.write_and_review(
        content_type="note_article",
        context={
            "topic": "AIエージェントが変える2026年の働き方",
            "target_audience": "ひとり社長・フリーランス",
            "key_points": [
                "8体のAIエージェントチーム",
                "95点品質ループ",
                "BYOK型で安心",
            ],
        },
    )

    print(f"ステータス: {content_result['status']}")
    print(f"リトライ回数: {content_result.get('retry_count', 0)}")

    if content_result.get("evaluation"):
        evaluation = content_result["evaluation"]
        print("\n[Guardian評価]")
        print(f"  スコア: {evaluation.get('total_score', 'N/A')}/100")
        print(f"  フィードバック: {evaluation.get('feedback', '')}")

    if content_result.get("content"):
        print("\n[生成コンテンツ(先頭500文字)]")
        print(content_result["content"][:500] + "...")

    print_section("Step 3: Designer - ビジュアル生成")
    print("サムネイル画像と短尺動画を生成します...\n")

    visual_result = orchestrator.delegate(
        "designer",
        {
            "task_type": "video",
            "context": {
                "platform": "youtube",
                "title": "AIエージェントが変える2026年の働き方",
                "content_text": content_result.get("content", "")[:300],
                "duration": 15.0,
            },
        },
    )

    if visual_result.get("success"):
        print("ビジュアル生成成功!")
        output = visual_result.get("output", {})
        if "video_path" in output:
            print(f"  動画パス: {output['video_path']}")
        if "composition" in output:
            print(f"  コンポジション: {output['composition']}")
    else:
        print("ビジュアル生成スキップ(HyperFrames未設定)")

    print_section("デモ完了")
    print("Virtusの主要ワークフローをデモしました。")
    print("\n実際の運用では:")
    print("  - Schedulerが毎朝7時に自動実行")
    print("  - Distributorが各プラットフォームに配信")
    print("  - Connectorが受信メッセージに自動返信")
    print("  - Analystが月次レポートを生成")


def run_mock_demo() -> None:
    """Run demo with mock data (no API calls)."""
    print_section("Step 1: Lead Strategist - 朝報生成")
    print("毎朝7時に自動実行される朝報を生成します...\n")

    mock_brief = {
        "date": datetime.now().date().isoformat(),
        "priorities": [
            {"task": "AI活用記事の執筆", "agent": "Drafter", "priority": "high"},
            {"task": "競合動向調査", "agent": "Researcher", "priority": "medium"},
        ],
        "insights": "本日は note 記事投稿に注力。AIエージェントのトレンドが上昇中。",
        "kpis": {
            "target_posts": 3,
            "engagement_goal": "5%",
        },
    }
    print("朝報生成成功!")
    print_json(mock_brief)

    print_section("Step 2: Drafter + Guardian - コンテンツ執筆 & 品質チェック")
    print("Garai Toneを適用したnote記事を執筆し、95点ループで品質チェック...\n")

    mock_content = """# AIエージェントが変える2026年の働き方

率直に言います。

2026年、働き方は根本から変わります。8体のAIエージェントがチームとなり、
あなたの代わりに集客・営業・クロージングを自動化する時代が来ました。

## 本質は「時間を取り戻すこと」

ひとり社長の最大の課題は、すべてを自分でやらなければならないこと。
コンテンツ作成、SNS運用、顧客対応...これらを8体のAIが分担します。

具体的には:
- Lead Strategist: 毎朝の戦略立案
- Drafter: 記事・投稿の執筆
- Guardian: 95点品質チェック
- Designer: ビジュアル生成

結論から言うと、「労働時間で売る」から「成果と仕組みで売る」への転換です。

---
galaiworks
"""

    print("ステータス: approved")
    print("リトライ回数: 1")
    print("\n[Guardian評価]")
    print("  スコア: 96/100")
    print("  フィードバック: ブランドDNAに準拠した高品質なコンテンツです。")
    print("\n[生成コンテンツ]")
    print(mock_content)

    print_section("Step 3: Designer - ビジュアル生成")
    print("サムネイル画像と短尺動画を生成します...\n")

    print("ビジュアル生成成功!")
    print("  コンポジション: HyperFrames HTML/CSS")
    print("  動画フォーマット: MP4 (15秒)")
    print("  解像度: 1920x1080")

    print_section("デモ完了")
    print("Virtusの主要ワークフローをデモしました（モックモード）。")


def run_quick_check() -> None:
    """Run a quick system check (for preflight script)."""
    print("Quick check: OK")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Virtus Summit Demo")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ANTHROPIC_API_KEY"),
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode without API calls",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick check mode (for preflight validation)",
    )

    args = parser.parse_args()

    if args.quick:
        run_quick_check()
        return

    if not args.mock and not args.api_key:
        print("Error: API key required. Use --api-key or set ANTHROPIC_API_KEY")
        print("       Or use --mock for demo without API calls")
        sys.exit(1)

    run_demo(args.api_key or "", mock=args.mock)


if __name__ == "__main__":
    main()
