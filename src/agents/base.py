"""エージェント基底クラス。

CLAUDE.md「エージェント実装の標準パターン」に準拠する。すべてのエージェントは
``BaseAgent`` を継承し ``execute()`` を実装する。

設計原則(CLAUDE.md / Officina §2):
- Anthropic Python SDK 経由で API 呼び出し(直接 HTTP 禁止)。
- ブランド DNA をすべてのエージェントが受け取り、出力に反映する。
- LLM クライアントは遅延生成する。API キーが無い環境(テスト・ドライラン)でも
  インポートとオフライン実行ができるようにするため。
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """エージェント 1 回の実行結果。

    Attributes:
        agent: 実行したエージェント名。
        output: 構造化された出力本体。
        content_type: Guardian が評価に使うコンテンツ種別(例 ``outreach_email``)。
        meta: 監査・後続処理向けの付帯情報。
    """

    agent: str
    output: dict[str, Any]
    content_type: str = "generic"
    meta: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """全エージェントの基底クラス。

    Args:
        model: 使用する Claude モデル ID。
        brand_dna: 顧客のブランド DNA(必須・出力に必ず反映)。
        api_key: Anthropic API キー。``None`` の場合は環境変数を参照し、
            それも無ければ LLM 呼び出し時にのみエラーとする(遅延生成)。
        skills: 呼び出し可能な galaiworks 独自スキル名のリスト。
        dry_run: ``True`` の場合 LLM を呼ばず決定論的なオフライン処理に徹する。
    """

    #: ゼロトラスト権限スコープ(``governance.permissions`` が参照)。
    name: str = "base"

    def __init__(
        self,
        model: str,
        brand_dna: dict[str, Any],
        api_key: str | None = None,
        skills: list[str] | None = None,
        dry_run: bool = False,
    ) -> None:
        self.model = model
        self.brand_dna = brand_dna
        self.skills = skills or []
        self.dry_run = dry_run
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client: Any = None  # 遅延生成

    @property
    def client(self) -> Any:
        """Anthropic クライアントを遅延生成して返す。"""
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY が未設定です。LLM 呼び出しには BYOK が必須です。"
                )
            from anthropic import Anthropic  # 遅延 import(オフライン実行のため)

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> AgentResult:
        """エージェントのメイン処理。

        Args:
            task: 上流(オーケストレーター)から渡される指示・入力。

        Returns:
            ``AgentResult``。
        """
        raise NotImplementedError

    def call_llm(
        self,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> str:
        """LLM 呼び出しの共通処理(Anthropic SDK 経由)。"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def brand_system_prompt(self, role: str) -> str:
        """ブランド DNA を必ず参照するシステムプロンプトを生成する。"""
        identity = self.brand_dna.get("identity", {})
        forbidden = self.brand_dna.get("forbidden", {})
        return (
            f"あなたは {identity.get('name', '顧客')} のための{role}エージェントです。\n"
            f"以下のブランド DNA を完全に遵守してください:\n{self.brand_dna}\n\n"
            f"絶対に避けるべき表現:\n{forbidden}\n"
        )
