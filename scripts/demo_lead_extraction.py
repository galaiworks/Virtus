#!/usr/bin/env python3
"""
Virtus Demo: PRタイムズ能動探索

サミット用デモスクリプト。
Researcher が PRタイムズからリードを抽出する様子を実演。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.researcher import Researcher


SAMPLE_BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
        "business": "AI 開発、SaaS、コンテンツ自動化",
        "target_audience": "ひとり社長・コーチ・コンサル・専門家",
        "target_industries": ["IT", "コンサルティング", "コーチング", "士業"],
    },
}


SAMPLE_PRESS_RELEASES = [
    {
        "title": "株式会社AIスタートアップ、シリーズAで5億円の資金調達を実施",
        "content": """
株式会社AIスタートアップ（代表取締役: 山田太郎）は、シリーズAラウンドにて
総額5億円の資金調達を実施したことをお知らせいたします。

今回の調達資金は、AI開発人材の採用強化、マーケティング施策の拡大に
充てる予定です。

当社は「AIで中小企業の生産性を10倍に」をミッションに掲げ、
現在急成長中のAIエージェント市場において...

課題: 多くの中小企業がAI導入に踏み切れていない現状があります。
        """,
        "url": "https://prtimes.jp/example1",
    },
    {
        "title": "コンサルティング会社DEF、代表の鈴木氏が経営者向けセミナーを開催",
        "content": """
DEFコンサルティング株式会社（代表: 鈴木花子、従業員5名）は、
中小企業経営者向けのDXセミナーを開催いたします。

「忙しすぎて新しいことに取り組めない」という経営者の声に応え...

当社は創業3年目、年商1.2億円を達成し、さらなる成長を目指しています。
        """,
        "url": "https://prtimes.jp/example2",
    },
    {
        "title": "大手製造業GHI、工場のDX化を推進",
        "content": """
株式会社GHI製造（従業員3000名、年商500億円）は、
全国10工場のDX化プロジェクトを発表しました。

大規模な設備投資により、生産効率を20%向上させる計画です。
        """,
        "url": "https://prtimes.jp/example3",
    },
    {
        "title": "コーチング事業を展開するJKL、オンラインプログラムを開始",
        "content": """
JKLコーチング（代表: 田中一郎、個人事業主）は、
経営者向けオンラインコーチングプログラムを開始いたします。

「売上は増えているが、自分の時間がない」という経営者の悩みに対応。

これまで月5名限定だったコーチングを、オンライン化により
月20名まで拡大します。
        """,
        "url": "https://prtimes.jp/example4",
    },
]


def demo_lead_extraction():
    """PRタイムズからのリード抽出デモ"""
    print("=" * 60)
    print("Virtus デモ: PRタイムズ能動探索")
    print("=" * 60)
    print()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEY が設定されていません")
        print("export ANTHROPIC_API_KEY=your_key_here")
        return

    print("1. Researcher を初期化中...")
    researcher = Researcher(
        api_key=api_key,
        model="claude-sonnet-4-6",
        brand_dna=SAMPLE_BRAND_DNA,
    )
    print("   完了")
    print()

    print("2. PRタイムズからリードを抽出中...")
    print(f"   (サンプルプレスリリース: {len(SAMPLE_PRESS_RELEASES)} 件)")
    print("   (Sonnet 4.6 を使用)")
    print()

    result = researcher.lead_extraction({
        "press_releases": SAMPLE_PRESS_RELEASES,
        "target_industries": ["IT", "コンサルティング", "コーチング"],
        "target_keywords": ["AI", "DX", "自動化", "生産性"],
    })

    print("-" * 60)
    print("【抽出されたリード】")
    print("-" * 60)

    if result.success:
        leads = result.content
        if leads:
            for i, lead in enumerate(leads, 1):
                print(f"\n--- リード {i} ---")
                print(f"会社名: {lead.get('company_name', '不明')}")
                print(f"決済権者: {lead.get('decision_maker', '不明')}")
                print(f"役職: {lead.get('title', '不明')}")
                print(f"ソース: {lead.get('source', '不明')}")

                score = lead.get('score', {})
                print(f"スコア:")
                print(f"  - 儲かってそう度: {score.get('wealth', 0)}/40")
                print(f"  - 決済権あり度: {score.get('authority', 0)}/30")
                print(f"  - 痛みあり度: {score.get('pain', 0)}/30")
                print(f"  - 合計: {score.get('total', 0):.1f}/100")
                print(f"理由: {lead.get('context', '不明')}")
        else:
            print("スコア60点以上のリードは見つかりませんでした")
    else:
        print(f"エラー: {result.error}")

    print()
    print(f"抽出完了: {result.metadata.get('count', 0)} 件")
    print()
    print("=" * 60)
    print("デモ完了")
    print("=" * 60)


if __name__ == "__main__":
    demo_lead_extraction()
