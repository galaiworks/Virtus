"""Connector - 関係構築・DM/コメント応対."""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent

CONNECTOR_SYSTEM = """あなたは Virtus の Connector エージェントです。

# あなたの使命
顧客 {customer_name} と見込み顧客の関係を、深く・自然に・人間らしく構築する。

# 顧客のブランド DNA
{brand_dna}

# 守るべき原則

第一に、テンプレ感を絶対に出さない。
{recipient_name} さん専用の文脈ある返信。

第二に、自動送信は禁止。生成は人間承認のためのドラフト。
あなたの仕事はドラフト生成までで、送信判断は人間が行う。

第三に、急かさない、押し付けない。売り込みより関係構築。

第四に、ブランド DNA の voice を完全継承。
顧客自身が書いたとしか思えないレベル。

第五に、過剰約束をしない。
「絶対」「必ず」「100%」等の保証表現は禁止。
"""


class Connector(BaseAgent):
    """関係構築エージェント.

    Phase 1: DM 返信ドラフト / アウトリーチ DM 草案生成のみ.
    送信は人間承認後のフローで別途実施.
    """

    SUPPORTED_TASKS = frozenset({"draft_dm_reply", "draft_outreach_dm"})

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("task_type")
        if task_type not in self.SUPPORTED_TASKS:
            raise ValueError(f"Connector は task_type={task_type} をサポートしていません")

        context = task.get("context", {}) or {}
        if task_type == "draft_dm_reply":
            return self.draft_dm_reply(context)
        return self.draft_outreach_dm(context)

    def draft_dm_reply(self, context: dict[str, Any]) -> dict[str, Any]:
        """既存スレッドへの返信ドラフトを生成."""
        system = self._build_system(context)
        history = context.get("interaction_history", [])
        incoming = context.get("incoming_message", {})
        platform = context.get("platform", "unknown")

        user_msg = (
            f"# プラットフォーム\n{platform}\n\n"
            f"# 過去のやり取り (新しい順)\n{history}\n\n"
            f"# 受信メッセージ\n{incoming}\n\n"
            "上記に対する返信ドラフトを 1 通だけ生成してください。"
            "前置きや説明は不要、本文のみ。"
        )
        text = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return {
            "task_type": "draft_dm_reply",
            "platform": platform,
            "draft": text,
            "requires_human_approval": True,
        }

    def draft_outreach_dm(self, context: dict[str, Any]) -> dict[str, Any]:
        """新規アウトリーチの DM 草案を生成 (LinkedIn / メール想定)."""
        system = self._build_system(context)
        recipient = context.get("recipient", {})
        prior_context = context.get("prior_context", "")
        cta = context.get("cta", "1on1 (15 分) のご相談")

        user_msg = (
            f"# 宛先\n{recipient}\n\n"
            f"# 過去の接点・文脈\n{prior_context or '(なし、初回コンタクト)'}\n\n"
            f"# CTA\n{cta}\n\n"
            "上記の宛先・文脈・CTA に基づき、アウトリーチ DM 草案を 1 通生成してください。\n"
            "- 250〜350 文字程度\n"
            "- 特電法を意識し、過去同意の有無を冒頭で確認する文脈がある場合は再確認の一文を入れる\n"
            "- 「絶対」「必ず」「100%」等の保証表現は使わない\n"
            "- 前置きや説明は不要、本文のみ"
        )
        text = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return {
            "task_type": "draft_outreach_dm",
            "recipient": recipient,
            "draft": text,
            "requires_human_approval": True,
        }

    def _build_system(self, context: dict[str, Any]) -> str:
        return CONNECTOR_SYSTEM.format(
            customer_name=context.get("customer_name", self.brand_dna.get("identity", {}).get("name", "顧客")),
            brand_dna=self.brand_dna_block(),
            recipient_name=context.get("recipient", {}).get("name", "相手"),
        )
