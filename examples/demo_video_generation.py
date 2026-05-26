"""Demo: Generate a video using Designer agent.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/demo_video_generation.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.designer import Designer


GALAIWORKS_BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
    },
    "visual": {
        "colors": ["#0a0e27", "#f5d547", "#ffffff"],
        "fonts": {
            "heading": "Noto Sans JP",
            "body": "Noto Sans JP",
        },
        "style": "professional",
    },
    "voice": {
        "tone": "プロフェッショナル × 親近感 × 直球",
    },
}


def demo_simple_video() -> None:
    """Demo 1: Create a simple title video."""
    print("\n=== Demo 1: シンプルなタイトル動画 ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "test-key")
    designer = Designer(
        api_key=api_key,
        brand_dna=GALAIWORKS_BRAND_DNA,
        output_dir=Path("./output"),
    )

    result = designer.execute({
        "task_type": "video",
        "context": {
            "platform": "youtube",
            "duration": 10.0,
            "output_name": "demo_simple",
            "elements": [
                {
                    "type": "title",
                    "text": "Virtus",
                    "start": 0,
                    "duration": 4,
                    "animate": "fade-in",
                },
                {
                    "type": "subtitle",
                    "text": "ひとり社長のためのAIエージェントチーム",
                    "start": 1,
                    "duration": 3,
                    "animate": "slide-up",
                },
                {
                    "type": "title",
                    "text": "今すぐ始める",
                    "start": 7,
                    "duration": 3,
                    "top": "85%",
                    "animate": "scale-in",
                },
            ],
        },
    })

    if result["success"]:
        print(f"成功: {result['video_path']}")
        print(f"   サイズ: {result['dimensions']}")
        print(f"   時間: {result['duration']}秒")
    else:
        print(f"失敗: {result.get('error')}")
        print(f"   HTMLプレビュー長: {len(result.get('html_preview', ''))}文字")


def demo_overlay_for_youtube() -> None:
    """Demo 2: YouTube用オーバーレイ動画生成."""
    print("\n=== Demo 2: YouTube用オーバーレイ ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "test-key")
    designer = Designer(
        api_key=api_key,
        brand_dna=GALAIWORKS_BRAND_DNA,
        output_dir=Path("./output"),
    )

    result = designer.execute({
        "task_type": "overlay",
        "context": {
            "platform": "youtube",
            "duration": 30.0,
            "output_name": "demo_overlay",
            "title": "AIエージェント時代の経営戦略",
            "subtitle": "2026年の最新動向",
            "lower_third": {
                "name": "ガライ",
                "title": "galaiworks 代表",
                "start": 5,
                "duration": 6,
            },
            "ctas": [
                {
                    "text": "チャンネル登録お願いします",
                    "start": 25,
                    "duration": 5,
                },
            ],
        },
    })

    if result["success"]:
        print(f"成功: {result['video_path']}")
    else:
        print(f"失敗: {result.get('error')}")


def demo_tiktok_format() -> None:
    """Demo 3: TikTok縦型動画."""
    print("\n=== Demo 3: TikTok縦型フック動画 ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "test-key")
    designer = Designer(
        api_key=api_key,
        brand_dna=GALAIWORKS_BRAND_DNA,
        output_dir=Path("./output"),
    )

    result = designer.execute({
        "task_type": "video",
        "context": {
            "platform": "tiktok",
            "duration": 15.0,
            "output_name": "demo_tiktok",
            "elements": [
                {
                    "type": "title",
                    "text": "知ってた？",
                    "start": 0,
                    "duration": 2,
                    "top": "30%",
                    "animate": "scale-in",
                },
                {
                    "type": "title",
                    "text": "AIで月100万",
                    "start": 2,
                    "duration": 3,
                    "top": "40%",
                    "animate": "slide-up",
                },
                {
                    "type": "subtitle",
                    "text": "自動化できる時代",
                    "start": 5,
                    "duration": 4,
                    "top": "55%",
                    "animate": "fade-in",
                },
                {
                    "type": "title",
                    "text": "詳しくはプロフへ",
                    "start": 11,
                    "duration": 4,
                    "top": "85%",
                    "animate": "scale-in",
                },
            ],
        },
    })

    if result["success"]:
        print(f"成功: {result['video_path']}")
        print(f"   フォーマット: 1080x1920 (9:16)")
    else:
        print(f"失敗: {result.get('error')}")


def demo_full_production_dryrun() -> None:
    """Demo 4: フル動画制作（ドライラン - 入力ファイルなし）."""
    print("\n=== Demo 4: フル動画制作パイプライン（ドライラン） ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "test-key")
    designer = Designer(
        api_key=api_key,
        brand_dna=GALAIWORKS_BRAND_DNA,
        output_dir=Path("./output"),
    )

    result = designer.execute({
        "task_type": "full_production",
        "context": {
            "input_path": "/path/to/raw_footage.mp4",
            "platform": "youtube",
            "title": "ひとり社長のAI活用法",
            "lower_third": {"name": "ガライ", "title": "galaiworks 代表"},
            "cta": "チャンネル登録お願いします",
            "output_name": "demo_full_production",
        },
    })

    print(f"想定パイプライン:")
    print(f"  1. Video-Use で素材編集（フィラー語削除、色補正）")
    print(f"  2. HyperFrames でオーバーレイ生成（タイトル、ローワーサード、CTA）")
    print(f"  3. FFmpeg で合成")
    print(f"結果: {result}")


if __name__ == "__main__":
    print("Virtus Designer Agent デモ")
    print("=" * 50)

    demo_simple_video()
    demo_overlay_for_youtube()
    demo_tiktok_format()
    demo_full_production_dryrun()

    print("\n" + "=" * 50)
    print("デモ終了")
    print("注: 実際の動画レンダリングには Node.js 22+ と FFmpeg が必要です")
    print("    インストール: npx skills add heygen-com/hyperframes")
