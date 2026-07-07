#!/usr/bin/env python3
"""Virtus CLI - Command line interface for Virtus operations.

Usage:
    python scripts/virtus.py morning-brief
    python scripts/virtus.py write --topic "AI活用術" --type note_article
    python scripts/virtus.py evaluate --content "コンテンツ..."
    python scripts/virtus.py onboard --customer-id new_customer
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_api_key() -> str:
    """Get API key from environment."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    return key


def load_brand_dna(customer_id: str = "galaiworks") -> dict:
    """Load brand DNA for a customer."""
    from scripts.demo import GALAIWORKS_BRAND_DNA

    if customer_id == "galaiworks":
        return GALAIWORKS_BRAND_DNA

    from src.brain import BrainLayer

    brain = BrainLayer()
    dna = brain.load_brand_dna(customer_id)
    if dna:
        return {
            "identity": dna.identity,
            "voice": dna.voice,
            "forbidden": dna.forbidden,
            "content_strategy": dna.content_strategy,
            "reference": dna.reference,
        }
    print(f"Warning: No brand DNA found for {customer_id}, using default")
    return GALAIWORKS_BRAND_DNA


def cmd_morning_brief(args: argparse.Namespace) -> None:
    """Generate morning brief."""
    from datetime import datetime

    from src.orchestrator import Orchestrator

    print("Generating morning brief...")
    orchestrator = Orchestrator(
        api_key=get_api_key(),
        brand_dna=load_brand_dna(args.customer),
    )

    result = orchestrator.morning_brief({"current_date": datetime.now().date().isoformat()})

    if result.get("success"):
        print("\n" + "=" * 50)
        print("Morning Brief")
        print("=" * 50)
        print(
            result["output"].get(
                "content", json.dumps(result["output"], ensure_ascii=False, indent=2)
            )
        )
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")


def cmd_write(args: argparse.Namespace) -> None:
    """Write and review content."""
    from src.orchestrator import Orchestrator

    print(f"Writing {args.type}: {args.topic}")
    orchestrator = Orchestrator(
        api_key=get_api_key(),
        brand_dna=load_brand_dna(args.customer),
    )

    result = orchestrator.write_and_review(
        content_type=args.type,
        context={
            "topic": args.topic,
            "target_audience": args.audience or "ひとり社長・フリーランス",
        },
    )

    print(f"\nStatus: {result['status']}")
    print(f"Retry count: {result.get('retry_count', 0)}")

    if result.get("evaluation"):
        print(f"Score: {result['evaluation'].get('total_score', 'N/A')}/100")

    if result.get("content"):
        print("\n" + "=" * 50)
        print("Generated Content")
        print("=" * 50)
        print(result["content"])


def cmd_evaluate(args: argparse.Namespace) -> None:
    """Evaluate content with Guardian."""
    from src.agents import Guardian

    content = args.content
    if args.file:
        content = Path(args.file).read_text()

    print("Evaluating content...")
    guardian = Guardian(
        api_key=get_api_key(),
        brand_dna=load_brand_dna(args.customer),
    )

    evaluation = guardian.evaluate(content, args.type)

    print(f"\nScore: {evaluation.total_score}/100")
    print(f"Verdict: {evaluation.verdict}")

    if evaluation.violations:
        print("\nViolations:")
        for v in evaluation.violations:
            print(f"  - [{v.severity}] {v.description}")

    if evaluation.feedback:
        print(f"\nFeedback: {evaluation.feedback}")


def cmd_onboard(args: argparse.Namespace) -> None:
    """Start onboarding for a new customer."""
    from src.onboarding import OnboardingFlow

    print(f"Starting onboarding for: {args.customer_id}")
    flow = OnboardingFlow(api_key=get_api_key())

    flow.start_session(args.customer_id)
    progress = flow.get_progress(args.customer_id)
    print(f"Session started. {progress['current']}/{progress['total']} questions answered.\n")

    while True:
        question = flow.get_current_question(args.customer_id)
        if not question:
            print("\nAll questions answered!")
            break

        print(f"\n[{question.id}] {question.category}")
        print(f"Q: {question.question}")

        answer = input("A: ").strip()
        if answer.lower() == "quit":
            print("Onboarding paused. Resume later with same customer ID.")
            break

        flow.submit_answer(args.customer_id, question.id, answer)
        progress = flow.get_progress(args.customer_id)
        print(f"Progress: {progress['current']}/{progress['total']}")

    if flow.get_progress(args.customer_id)["completed"]:
        print("\nGenerating Brand DNA...")
        brand_dna = flow.generate_brand_dna(args.customer_id)
        if brand_dna:
            print("Brand DNA generated successfully!")
            print(f"Name: {brand_dna.identity.get('name', 'N/A')}")
            print(f"Voice tone: {brand_dna.voice.get('tone', 'N/A')}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show system status."""
    import subprocess

    print("Virtus System Status")
    print("=" * 50)

    result = subprocess.run(
        ["python", "scripts/preflight.py"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Virtus CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--customer",
        default="galaiworks",
        help="Customer ID for brand DNA (default: galaiworks)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # morning-brief
    sub = subparsers.add_parser("morning-brief", help="Generate morning brief")
    sub.set_defaults(func=cmd_morning_brief)

    # write
    sub = subparsers.add_parser("write", help="Write and review content")
    sub.add_argument("--topic", required=True, help="Content topic")
    sub.add_argument("--type", default="note_article", help="Content type")
    sub.add_argument("--audience", help="Target audience")
    sub.set_defaults(func=cmd_write)

    # evaluate
    sub = subparsers.add_parser("evaluate", help="Evaluate content with Guardian")
    sub.add_argument("--content", help="Content text to evaluate")
    sub.add_argument("--file", help="File containing content")
    sub.add_argument("--type", default="note_article", help="Content type")
    sub.set_defaults(func=cmd_evaluate)

    # onboard
    sub = subparsers.add_parser("onboard", help="Start customer onboarding")
    sub.add_argument("--customer-id", required=True, help="New customer ID")
    sub.set_defaults(func=cmd_onboard)

    # status
    sub = subparsers.add_parser("status", help="Show system status")
    sub.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
