#!/usr/bin/env python3
"""Pre-flight check script for Virtus Summit demo.

Run this before the demo to verify everything is ready.

Usage:
    python scripts/preflight.py
    python scripts/preflight.py --full  # Include API test
"""

import argparse
import subprocess
import sys
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")


def print_check(name: str, passed: bool, detail: str = "") -> None:
    status = f"{Colors.GREEN}[OK]{Colors.RESET}" if passed else f"{Colors.RED}[NG]{Colors.RESET}"
    print(f"  {status} {name}")
    if detail and not passed:
        print(f"       {Colors.YELLOW}{detail}{Colors.RESET}")


def print_warning(text: str) -> None:
    print(f"  {Colors.YELLOW}[WARN] {text}{Colors.RESET}")


def check_python_version() -> bool:
    version = sys.version_info
    return version.major >= 3 and version.minor >= 11


def check_dependencies() -> tuple[bool, str]:
    try:
        import anthropic  # noqa: F401
        import yaml  # noqa: F401
        return True, ""
    except ImportError as e:
        return False, f"Missing: {e.name}"


def check_project_structure() -> tuple[bool, list[str]]:
    required = [
        "src/agents/__init__.py",
        "src/orchestrator.py",
        "src/scheduler.py",
        "src/brain.py",
        "src/onboarding.py",
        "scripts/demo.py",
        ".claude/skills/garai-tone/SKILL.md",
    ]
    missing = []
    for path in required:
        if not Path(path).exists():
            missing.append(path)
    return len(missing) == 0, missing


def check_tests() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            last_line = lines[-1] if lines else ""
            return True, last_line
        return False, result.stdout.split("\n")[-1] if result.stdout else "Tests failed"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def check_mock_demo() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["python", "scripts/demo.py", "--mock", "--quick"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr[:100] if result.stderr else "Failed"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def check_api_key() -> tuple[bool, str]:
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return False, "ANTHROPIC_API_KEY not set"
    if not key.startswith("sk-"):
        return False, "Invalid key format"
    return True, f"...{key[-8:]}"


def check_api_connection() -> tuple[bool, str]:
    try:
        import os
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        return True, response.content[0].text[:20]
    except Exception as e:
        return False, str(e)[:50]


def check_disk_space() -> tuple[bool, str]:
    import shutil
    total, used, free = shutil.disk_usage(".")
    free_gb = free // (1024 ** 3)
    if free_gb < 1:
        return False, f"Only {free_gb}GB free"
    return True, f"{free_gb}GB free"


def check_brain_directory() -> tuple[bool, str]:
    brain_path = Path("brain")
    if brain_path.exists():
        gitignore = brain_path / ".gitignore"
        if gitignore.exists():
            return True, "Protected by .gitignore"
        return False, ".gitignore missing"
    return True, "Not created yet (OK)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Virtus pre-flight check")
    parser.add_argument("--full", action="store_true", help="Include API connection test")
    args = parser.parse_args()

    print_header("Virtus Pre-flight Check")
    print(f"Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")

    all_passed = True

    # Python version
    print_header("Environment")
    passed = check_python_version()
    print_check(f"Python {sys.version_info.major}.{sys.version_info.minor}", passed)
    all_passed &= passed

    # Dependencies
    passed, detail = check_dependencies()
    print_check("Dependencies installed", passed, detail)
    all_passed &= passed

    # Disk space
    passed, detail = check_disk_space()
    print_check(f"Disk space ({detail})", passed)
    all_passed &= passed

    # Project structure
    print_header("Project Structure")
    passed, missing = check_project_structure()
    print_check("Required files exist", passed, f"Missing: {missing}" if missing else "")
    all_passed &= passed

    # Brain directory
    passed, detail = check_brain_directory()
    print_check(f"Brain directory ({detail})", passed)
    all_passed &= passed

    # Tests
    print_header("Tests")
    print("  Running tests... (this may take a moment)")
    passed, detail = check_tests()
    print_check(f"All tests pass ({detail})", passed, detail if not passed else "")
    all_passed &= passed

    # Mock demo
    print_header("Demo")
    passed, detail = check_mock_demo()
    print_check("Mock demo runs", passed, detail)
    all_passed &= passed

    # API (optional)
    if args.full:
        print_header("API Connection")
        passed, detail = check_api_key()
        print_check(f"API key configured ({detail})", passed, detail if not passed else "")
        all_passed &= passed

        if passed:
            print("  Testing API connection...")
            passed, detail = check_api_connection()
            print_check(f"API responds ({detail})", passed, detail if not passed else "")
            all_passed &= passed
    else:
        print_warning("Skipping API test (use --full to include)")

    # Summary
    print_header("Summary")
    if all_passed:
        print(f"  {Colors.GREEN}{Colors.BOLD}All checks passed! Ready for demo.{Colors.RESET}")
        return 0
    else:
        print(f"  {Colors.RED}{Colors.BOLD}Some checks failed. Please fix before demo.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
