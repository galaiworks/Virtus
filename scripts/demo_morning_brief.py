#!/usr/bin/env python3
"""
Virtus Demo: 朝報生成

サミット用デモスクリプト。
Lead Strategist が朝報を生成する様子を実演。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.lead_strategist import LeadStrategist
from src.agents.researcher import Researcher


SAMPLE_BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
        "business": "AI 開発、SaaS、コンテンツ自動化",
        "target_audience": "ひとり社長・コーチ・コンサル・専門家",
    },
    "voice": {
        "tone": "プロフェッショナル × 親近感 × 直球",
        "personality": [
            "率直、嘘や曖昧さを嫌う",
            "海外動向に詳しい",
            "数字に強い",
        ],
        "preferred": [
            "率直に言うと",
            "本質は",
            "結論から言うと",
        ],
    },
    "forbidden": [
        "絶対",
        "必ず",
        "100%",
        "簡単に",
        "誰でも稼げる",
    ],
}


def demo_morning_brief():
    """朝報生成デモ"""
    print("=" * 60)
    print("Virtus デモ: 朝報生成")
    print("=" * 60)
    print()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません")
        print("export ANTHROPIC_API_KEY=your_key_here")
        return

    print("1. Lead Strategist を初期化中...")
    lead_strategist = LeadStrategist(
        api_key=api_key,
        model="claude-opus-4-7",
        brand_dna=SAMPLE_BRAND_DNA,
    )
    print("   完了")
    print()

    print("2. 朝報を生成中...")
    print("   (Opus 4.7 を使用)")
    print()

    context = {
        "yesterday_summary": """
- note 記事「AIエージェント入門」を公開、PV 850
- X でスレッド投稿、インプレッション 12,500
- DM 返信 3 件完了
- 新規リード 2 件獲得（PRタイムズ経由）
        """,
        "new_leads": """
- 株式会社ABC（資金調達 5 億円発表、決済権者: 代表 山田氏）
- DEF コンサルティング（AI 導入検討中、担当: 鈴木氏）
        """,
        "weekly_goals": """
- note 記事: 2本（今週 0/2）
- X 投稿: 20本（今週 8/20）
- 商談設定: 3件（今週 1/3）
        """,
        "trends": """
- Anthropic が Claude 4.7 を発表、エージェント性能が大幅向上
- AI エージェント市場、2026 年に $50B 規模に
- 日本でも「AI 社長」への関心が急増中
        """,
    }

    result = lead_strategist.morning_brief({"context": context})

    print("-" * 60)
    print("【朝報】")
    print("-" * 60)

    if result.success:
        print(result.content)
    else:
        print(f"エラー: {result.error}")

    print()
    print("=" * 60)
    print("デモ完了")
    print("=" * 60)


if __name__ == "__main__":
    demo_morning_brief()
