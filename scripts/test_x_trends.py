#!/usr/bin/env python3
"""Test X trend research with Researcher agent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock

from src.agents import Researcher

BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
        "primary_target_audience": "ひとり社長・コーチ・コンサル",
    },
    "voice": {"tone": "プロフェッショナル × 親近感"},
    "content_strategy": {
        "pillar_topics": ["AIエージェント", "自動化戦略", "海外AI動向"],
    },
}

# 2026年5月のXトレンドデータ（WebSearchで取得）
X_TREND_DATA = [
    {
        "title": "Xアルゴリズム2026最新解説",
        "url": "https://marketdive.net/x-twitter-algorithm-2026/",
        "content": """
        2026年5月、Xはアルゴリズムの追加アップデートを公開。
        - AIが「リアクションの深さ」を予測し、いいね数だけでなく滞在時間を重視
        - 4K画像タップ、Grok動くヘッダーなどインタラクティブコンテンツが有利
        - スパム判定が厳格化、テーマ整合性が重要に
        """,
    },
    {
        "title": "日本人631名のX購買行動調査2026",
        "url": "https://mantan-web.jp/prtimes/article/20260501prt00m200000648a.html",
        "content": """
        - 日本ユーザーの約40%がX経由で月1回以上購入
        - 20代は約24%が週1回購入
        - インフルエンサーより専門家の投稿を信頼する傾向
        """,
    },
    {
        "title": "2026年トレンド予測：X企業投稿成功事例",
        "url": "https://www.comnico.jp/we-love-social/best-x-posted-case-2025",
        "content": """
        - UGC（ユーザー生成コンテンツ）活用が増加
        - リアルタイムマーケティングが効果的
        - 縦型動画コンテンツの伸び
        """,
    },
    {
        "title": "XからAIが予測、26年の大ヒット候補",
        "url": "https://xtrend.nikkei.com/atcl/contents/18/01083/00005/",
        "content": """
        - AIアシスタントの一般化
        - パーソナライズされた自動化ツール
        - ひとり社長向けAIサービスの台頭
        """,
    },
]


def test_trend_research_with_x_data():
    """Test Researcher with actual X trend data."""
    print("=" * 60)
    print("Researcher Agent - X トレンドリサーチテスト")
    print("=" * 60)

    researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)

    # Mock the LLM call
    mock_response = """【業界トレンド (2026年5月)】

1. Xアルゴリズム変更 - 「リアクションの深さ」重視
   - 概要: 2026年5月、XはAIによる「リアクションの深さ」予測を導入。いいね数だけでなく滞在時間やエンゲージメント質を評価。
   - 影響度: 高
   - ソース: https://marketdive.net/x-twitter-algorithm-2026/
   - 顧客への意味: ひとり社長は「深い価値」を提供するコンテンツに注力すべき。短絡的なバズ狙いは逆効果。

2. X経由購買行動の活発化
   - 概要: 日本ユーザーの40%がX経由で月1回以上購入。20代は24%が週1回購入。
   - 影響度: 高
   - ソース: https://mantan-web.jp/prtimes/article/20260501prt00m200000648a.html
   - 顧客への意味: Xは「認知」だけでなく「購買」チャネルとして機能。CTAを明確にした投稿が有効。

3. ひとり社長向けAIサービスの台頭
   - 概要: 日経トレンドがAI予測で「ひとり社長向けAIサービス」を2026年ヒット候補に選出。
   - 影響度: 中
   - ソース: https://xtrend.nikkei.com/atcl/contents/18/01083/00005/
   - 顧客への意味: Virtusの市場タイミングは最適。競合が増える前に先行者優位を確立すべき。

【顧客への提言】
- Xアルゴリズム変更に対応し、「深いエンゲージメント」を生むコンテンツ戦略へシフト
- 購買行動データを活かし、CTA付き投稿を増やす
- 「ひとり社長×AI」の文脈でポジショニングを強化"""

    researcher.call_llm = MagicMock(return_value=mock_response)

    result = researcher.execute({
        "task_type": "trend_research",
        "context": {
            "target_keywords": ["AI", "ひとり社長", "自動化", "Xアルゴリズム"],
            "source_materials": X_TREND_DATA,
            "period": "2026年5月",
            "competitors": ["いいねAI", "NoimosAI"],
        },
    })

    print(f"\nステータス: {'成功' if result['success'] else '失敗'}")
    print(f"タスクタイプ: {result['task_type']}")
    print(f"期間: {result['output']['period']}")
    print("\n" + "-" * 60)
    print("【リサーチ結果】")
    print("-" * 60)
    print(result["output"]["content"])

    # Assertions
    assert result["success"] is True
    assert result["task_type"] == "trend_research"
    assert "2026年5月" in result["output"]["period"]
    assert "content" in result["output"]

    print("\n" + "=" * 60)
    print("テスト完了: PASSED")
    print("=" * 60)

    return result


def test_trend_research_live():
    """Test with live API (requires ANTHROPIC_API_KEY)."""
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Skipping live test.")
        return None

    print("=" * 60)
    print("Researcher Agent - X トレンドリサーチ (LIVE API)")
    print("=" * 60)

    researcher = Researcher(api_key=api_key, brand_dna=BRAND_DNA)

    result = researcher.execute({
        "task_type": "trend_research",
        "context": {
            "target_keywords": ["AI", "ひとり社長", "自動化"],
            "source_materials": X_TREND_DATA,
            "period": "2026年5月",
        },
    })

    print(f"\nステータス: {'成功' if result['success'] else '失敗'}")
    print("\n【リサーチ結果】")
    print(result["output"]["content"])

    return result


if __name__ == "__main__":
    # Run mock test
    test_trend_research_with_x_data()

    print("\n")

    # Optionally run live test
    if "--live" in sys.argv:
        test_trend_research_live()
