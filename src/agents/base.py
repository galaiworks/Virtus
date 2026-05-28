"""BaseAgent - 全 Virtus エージェントの基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from anthropic import Anthropic

from src.brand_dna import format_brand_dna


class BaseAgent(ABC):
    """全 Virtus エージェントが継承する基底クラス.

    CLAUDE.md の標準パターンに準拠.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
        client: Anthropic | None = None,
    ) -> None:
        """エージェントを初期化.

        Args:
            api_key: Anthropic API キー (BYOK).
            model: 使用するモデル ID.
            brand_dna: 顧客のブランド DNA 辞書.
            skills: 適用するスキル名のリスト.
            client: 既存の Anthropic クライアント (テスト時の注入用).
        """
        self.api_key = api_key
        self.model = model
        self.brand_dna = brand_dna
        self.skills = skills or []
        self.client = client or Anthropic(api_key=api_key)

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """エージェントのメイン処理."""
        ...

    def call_llm(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """LLM 呼び出しの共通処理.

        Args:
            system: システムプロンプト.
            messages: ユーザー / アシスタント交互のメッセージ.
            max_tokens: 最大出力トークン.

        Returns:
            LLM の最初の text コンテンツ.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def brand_dna_block(self) -> str:
        """システムプロンプトに埋め込む用の整形済みブランド DNA."""
        return format_brand_dna(self.brand_dna)
