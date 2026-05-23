#!/usr/bin/env python3
"""
Virtus Demo: 95点品質ループ

サミット用デモスクリプト。
Guardian が品質チェックを行い、Drafter にフィードバックする様子を実演。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.drafter import Drafter
from src.agents.guardian import Guardian


SAMPLE_BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
        "business": "AI 開発、SaaS、コンテンツ自動化",
    },
    "voice": {
        "tone": "プロフェッショナル × 親近感 × 直球",
        "preferred": ["率直に言うと", "本質は", "結論から言うと"],
    },
    "forbidden": ["絶対", "必ず", "100%", "簡単に", "誰でも稼げる"],
}


def demo_quality_loop():
    """95点品質ループデモ"""
    print("=" * 60)
    print("Virtus デモ: Guardian 95点品質ループ")
    print("=" * 60)
    print()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません")
        print("export ANTHROPIC_API_KEY=your_key_here")
        return

    print("1. Guardian と Drafter を初期化中...")
    guardian = Guardian(
        api_key=api_key,
        model="claude-opus-4-7",
        brand_dna=SAMPLE_BRAND_DNA,
    )
    drafter = Drafter(
        api_key=api_key,
        model="claude-sonnet-4-6",
        brand_dna=SAMPLE_BRAND_DNA,
    )
    print("   完了")
    print()

    test_contents = [
        {
            "name": "過剰約束コンテンツ",
            "content": """
AIエージェントを導入すれば、絶対に売上が100%アップします！
誰でも簡単に始められて、必ず成功できます。
今すぐ始めましょう！
            """,
            "content_type": "x_post",
        },
        {
            "name": "法令違反コンテンツ（メール）",
            "content": """
こんにちは！

弊社の新サービスをご案内いたします。
AIで業務効率化を実現できます。

ぜひご検討ください。
            """,
            "content_type": "email",
        },
        {
            "name": "適切なコンテンツ",
            "content": """
率直に言うと、AIエージェントは「適切に設計すれば」
業務効率を大幅に改善できます。

Anthropic の調査によると、導入企業の78%が
業務時間を30%以上削減しています。

ただし、成功には適切な設計と運用が必要です。
まずは無料診断で、あなたの業務に合うか確認しましょう。

---
配信解除はこちら: [配信解除リンク]
送信者: galaiworks
            """,
            "content_type": "email",
        },
    ]

    for test in test_contents:
        print("-" * 60)
        print(f"【テスト】{test['name']}")
        print(f"コンテンツタイプ: {test['content_type']}")
        print("-" * 60)
        print()
        print("コンテンツ:")
        print(test["content"].strip())
        print()

        print("Guardian が評価中...")
        result = guardian.execute({
            "type": "evaluate",
            "content": test["content"],
            "content_type": test["content_type"],
        })

        if result.success:
            content = result.content
            score = content.get("total_score", 0)
            approved = content.get("approved", False)

            print(f"\n📊 評価結果:")
            print(f"   合計スコア: {score}/100")
            print(f"   承認: {'✅ はい' if approved else '❌ いいえ'}")

            axis_scores = content.get("axis_scores", {})
            print(f"\n   軸別スコア:")
            print(f"   - ブランドDNA: {axis_scores.get('brand_dna', 0)}/25")
            print(f"   - 法令遵守: {axis_scores.get('legal', 0)}/25")
            print(f"   - コンテンツ品質: {axis_scores.get('quality', 0)}/20")
            print(f"   - ターゲット適合: {axis_scores.get('target_fit', 0)}/15")
            print(f"   - 過剰約束: {axis_scores.get('overpromise', 0)}/10")
            print(f"   - ハルシネーション: {axis_scores.get('hallucination', 0)}/5")

            violations = content.get("violations", [])
            if violations:
                print(f"\n   ⚠️ 違反検出 ({len(violations)}件):")
                for v in violations[:5]:
                    severity = v.get("severity", "?")
                    category = v.get("category", "?")
                    description = v.get("description", "?")
                    print(f"   - [{severity}] {category}: {description}")

            if not approved:
                print(f"\n   💡 フィードバック:")
                print(f"   {content.get('feedback', 'なし')[:200]}...")
        else:
            print(f"エラー: {result.error}")

        print()

    print("=" * 60)
    print("デモ完了")
    print("=" * 60)
    print()
    print("ポイント:")
    print("- Guardian は Opus 4.7 を使用（高精度な品質判定）")
    print("- 95点未満は承認しない（神さんの教え）")
    print("- 具体的な改善フィードバックを提供")
    print("- 法令遵守も自動チェック")


if __name__ == "__main__":
    demo_quality_loop()
