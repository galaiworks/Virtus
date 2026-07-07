"""Drafter - 全コンテンツ執筆エージェント (Garai Tone / DREAM WRITING / IMPACT v2.0R)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent

# CWD に依存せず、常にリポジトリルート配下のスキル定義を参照する
SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"

DRAFTER_SYSTEM = """あなたは Virtus の Drafter エージェントです。

# あなたの使命
顧客のブランド DNA を完全継承し、顧客自身が書いたとしか思えないコンテンツを生成する。

# 顧客のブランド DNA
{brand_dna}

# 適用するスキル
{skills}

# 守るべき原則

第一に、ブランド DNA の voice を完全に反映する。
顧客の signature_phrases、vocabulary.preferred を自然に織り込む。

第二に、禁止表現を絶対に使わない。
特に「絶対」「必ず」「100%」等は景表法違反リスク。

第三に、過剰約束をしない。
具体的に書く一方で、保証はしない。

第四に、Garai Tone の基本原則を守る。
- 結論先出し (最初の 2 行で何を伝えるか示す)
- 具体例または数字を必ず 1 つ以上含める
- 一文 40 文字以内推奨、最大 60 文字
- 最後に CTA を配置
"""


class Drafter(BaseAgent):
    """執筆エージェント.

    Skills (Garai Tone, DREAM WRITING, IMPACT v2.0R) をシステムプロンプトに注入する.
    """

    SUPPORTED_TASKS = frozenset(
        {"write", "refine", "morning_brief_body", "outreach_dm"}
    )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """執筆タスクを実行."""
        task_type = task.get("task_type")
        if task_type not in self.SUPPORTED_TASKS:
            raise ValueError(f"Drafter は task_type={task_type} をサポートしていません")

        if task_type == "refine":
            return self.refine(task["content"], task["feedback"])
        return self.write(
            content_type=task_type,
            brief=task.get("brief", ""),
            extra_context=task.get("context", {}),
        )

    def write(
        self,
        content_type: str,
        brief: str,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """新規執筆.

        Args:
            content_type: "write" | "outreach_dm" | "morning_brief_body" など.
            brief: 何を書くかの指示.
            extra_context: 補足情報.

        Returns:
            {"task_type": content_type, "output": "...本文..."}.
        """
        system = self._build_system_prompt()
        user_msg = f"# 依頼内容 ({content_type})\n\n{brief}"
        if extra_context:
            user_msg += f"\n\n# 追加コンテキスト\n{extra_context}"

        text = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return {"task_type": content_type, "output": text}

    def refine(self, content: str, feedback: str) -> dict[str, Any]:
        """Guardian からの差し戻しに応じて改稿.

        Args:
            content: 元のコンテンツ.
            feedback: Guardian からの具体的指示.
        """
        system = self._build_system_prompt()
        user_msg = (
            "以下のコンテンツを Guardian の指摘に従って改稿してください。\n"
            "ブランド DNA は完全継承、禁止表現は使わない。\n\n"
            f"# 元のコンテンツ\n{content}\n\n"
            f"# Guardian からの指摘\n{feedback}\n\n"
            "改稿版だけを返してください (前置きや説明は不要)。"
        )
        text = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return {"task_type": "refine", "output": text}

    def _build_system_prompt(self) -> str:
        """スキル定義をロードしてシステムプロンプトに埋め込む."""
        skill_blocks = [self._load_skill(name) for name in self.skills]
        skill_text = "\n\n".join(filter(None, skill_blocks)) or "(スキル指定なし)"
        return DRAFTER_SYSTEM.format(
            brand_dna=self.brand_dna_block(),
            skills=skill_text,
        )

    @staticmethod
    def _load_skill(skill_name: str) -> str:
        """`.claude/skills/{name}/SKILL.md` をロード."""
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_path.exists():
            return f"## {skill_name}\n(SKILL.md が見つかりません: {skill_path})"
        return f"## スキル: {skill_name}\n\n{skill_path.read_text(encoding='utf-8')}"
