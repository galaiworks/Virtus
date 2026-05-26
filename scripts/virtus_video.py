"""CLI for Virtus video generation.

Usage:
    # Simple video from text
    python scripts/virtus_video.py create \\
        --platform youtube \\
        --title "タイトル" \\
        --subtitle "サブタイトル" \\
        --duration 10 \\
        --output my_video

    # Full production from raw footage
    python scripts/virtus_video.py produce \\
        --input raw.mp4 \\
        --platform youtube \\
        --title "タイトル" \\
        --speaker "ガライ" \\
        --role "CEO" \\
        --cta "登録お願いします" \\
        --output final

    # Edit footage only
    python scripts/virtus_video.py edit \\
        --input raw.mp4 \\
        --output edited \\
        --no-subtitles
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.designer import Designer


def load_brand_dna(customer_id: str | None) -> dict:
    """Load brand DNA for a customer or use default."""
    if customer_id:
        brand_path = Path(f"brain/customers/{customer_id}/brand-dna.json")
        if brand_path.exists():
            return json.loads(brand_path.read_text())

    return {
        "identity": {"name": "Default"},
        "visual": {
            "colors": ["#0a0e27", "#f5d547", "#ffffff"],
            "fonts": {"heading": "Noto Sans JP", "body": "Noto Sans JP"},
            "style": "professional",
        },
    }


def cmd_create(args: argparse.Namespace) -> int:
    """Create a video from scratch."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        return 1

    brand_dna = load_brand_dna(args.customer)
    designer = Designer(
        api_key=api_key,
        brand_dna=brand_dna,
        output_dir=Path(args.output_dir),
    )

    elements = []
    if args.title:
        elements.append({
            "type": "title",
            "text": args.title,
            "start": 0,
            "duration": min(4, args.duration),
            "animate": "fade-in",
        })
    if args.subtitle:
        elements.append({
            "type": "subtitle",
            "text": args.subtitle,
            "start": 1,
            "duration": min(3, args.duration - 1),
            "animate": "slide-up",
        })
    if args.cta:
        elements.append({
            "type": "title",
            "text": args.cta,
            "start": args.duration - 3,
            "duration": 3,
            "top": "85%",
            "animate": "scale-in",
        })

    result = designer.execute({
        "task_type": "video",
        "context": {
            "platform": args.platform,
            "duration": args.duration,
            "output_name": args.output,
            "elements": elements,
        },
    })

    if result["success"]:
        print(f"動画生成完了: {result['video_path']}")
        return 0
    else:
        print(f"失敗: {result.get('error')}", file=sys.stderr)
        return 1


def cmd_produce(args: argparse.Namespace) -> int:
    """Full video production from raw footage."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        return 1

    brand_dna = load_brand_dna(args.customer)
    designer = Designer(
        api_key=api_key,
        brand_dna=brand_dna,
        output_dir=Path(args.output_dir),
    )

    context = {
        "input_path": args.input,
        "platform": args.platform,
        "output_name": args.output,
        "remove_filler_words": not args.keep_fillers,
        "remove_silence": not args.keep_silence,
        "color_grade": not args.no_color_grade,
    }
    if args.title:
        context["title"] = args.title
    if args.speaker:
        context["lower_third"] = {
            "name": args.speaker,
            "title": args.role or "",
        }
    if args.cta:
        context["cta"] = args.cta

    result = designer.execute({
        "task_type": "full_production",
        "context": context,
    })

    if result["success"]:
        print(f"動画制作完了: {result['video_path']}")
        if "steps" in result:
            print(f"   編集: {result['steps'].get('edit')}")
            print(f"   オーバーレイ: {result['steps'].get('overlay')}")
            print(f"   合成: {result['steps'].get('merged')}")
        return 0
    else:
        print(f"失敗: {result.get('error')}", file=sys.stderr)
        return 1


def cmd_edit(args: argparse.Namespace) -> int:
    """Edit raw footage."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        return 1

    brand_dna = load_brand_dna(args.customer)
    designer = Designer(
        api_key=api_key,
        brand_dna=brand_dna,
        output_dir=Path(args.output_dir),
    )

    result = designer.execute({
        "task_type": "edit_footage",
        "context": {
            "input_path": args.input,
            "output_name": args.output,
            "remove_filler_words": not args.keep_fillers,
            "remove_silence": not args.keep_silence,
            "color_grade": not args.no_color_grade,
            "auto_subtitles": not args.no_subtitles,
            "subtitle_style": args.subtitle_style,
            "target_duration": args.target_duration,
        },
    })

    if result["success"]:
        print(f"編集完了: {result['video_path']}")
        print(f"   時間: {result['duration']}秒")
        return 0
    else:
        print(f"失敗: {result.get('error')}", file=sys.stderr)
        return 1


def cmd_clips(args: argparse.Namespace) -> int:
    """Extract best clips from a long video."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        return 1

    brand_dna = load_brand_dna(args.customer)
    designer = Designer(
        api_key=api_key,
        brand_dna=brand_dna,
        output_dir=Path(args.output_dir),
    )

    result = designer.extract_clips({
        "context": {
            "input_path": args.input,
            "num_clips": args.num_clips,
            "clip_duration": args.clip_duration,
        },
    })

    if result["success"]:
        print(f"{result['total_clips']}本のクリップを抽出")
        for clip in result["clips"]:
            print(f"   - {clip['path']} ({clip['duration']}秒)")
        return 0
    else:
        print("クリップ抽出失敗", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Virtus 動画生成・編集 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--customer", help="顧客ID")
    parser.add_argument("--output-dir", default="./output", help="出力ディレクトリ")

    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="新規動画生成")
    create.add_argument("--platform", default="youtube",
                        choices=["youtube", "youtube_shorts", "instagram_feed",
                                 "instagram_story", "instagram_reel", "tiktok",
                                 "linkedin", "x_video"])
    create.add_argument("--title", help="タイトル")
    create.add_argument("--subtitle", help="サブタイトル")
    create.add_argument("--cta", help="CTA文言")
    create.add_argument("--duration", type=float, default=10.0, help="動画時間（秒）")
    create.add_argument("--output", default="video", help="出力ファイル名")
    create.set_defaults(func=cmd_create)

    produce = subparsers.add_parser("produce", help="フル動画制作")
    produce.add_argument("--input", required=True, help="入力動画")
    produce.add_argument("--platform", default="youtube")
    produce.add_argument("--title", help="タイトル")
    produce.add_argument("--speaker", help="話者名")
    produce.add_argument("--role", help="話者役職")
    produce.add_argument("--cta", help="CTA文言")
    produce.add_argument("--keep-fillers", action="store_true", help="フィラー語を残す")
    produce.add_argument("--keep-silence", action="store_true", help="無音を残す")
    produce.add_argument("--no-color-grade", action="store_true", help="色補正なし")
    produce.add_argument("--output", default="final", help="出力ファイル名")
    produce.set_defaults(func=cmd_produce)

    edit = subparsers.add_parser("edit", help="素材編集のみ")
    edit.add_argument("--input", required=True)
    edit.add_argument("--output", default="edited")
    edit.add_argument("--keep-fillers", action="store_true")
    edit.add_argument("--keep-silence", action="store_true")
    edit.add_argument("--no-color-grade", action="store_true")
    edit.add_argument("--no-subtitles", action="store_true", help="字幕生成なし")
    edit.add_argument("--subtitle-style", default="modern")
    edit.add_argument("--target-duration", type=float, help="目標時間（秒）")
    edit.set_defaults(func=cmd_edit)

    clips = subparsers.add_parser("clips", help="ベストクリップ抽出")
    clips.add_argument("--input", required=True)
    clips.add_argument("--num-clips", type=int, default=5)
    clips.add_argument("--clip-duration", type=float, default=15.0)
    clips.set_defaults(func=cmd_clips)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
