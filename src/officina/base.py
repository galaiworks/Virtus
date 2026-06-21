"""Officina エージェント基底クラス。

CLAUDE.md の ``BaseAgent`` パターンを踏襲しつつ、Officina の原則を加える:

- 各エージェントは自分の許可スコープ(:func:`officina.gates.permission_scope_gate`)を
  通った行為のみ実行する(ゼロトラスト)。
- 各ステージは「合格ゲート(テストスイート相当)」を ``acceptance_gate`` として持つ。
- 生成と検証を兼務しない(検証は独立した Guardian が行う)。

注意: 実際の LLM 呼び出しは Anthropic Python SDK 経由で行う(直接 HTTP 禁止)。
本モジュールは SDK 未インストール環境でも import できるよう、遅延 import にする。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from officina.gates import GateResult, permission_scope_gate


class BaseAgent(ABC):
    """全 Officina エージェントの基底クラス。

    Attributes:
        name: エージェント名(:data:`officina.gates.AGENT_PERMISSIONS` のキーと一致)。
        model: 使用する Claude モデル ID。
        brand_dna: 顧客のブランド DNA(全出力に反映必須)。
        skills: 呼び出し可能な galaiworks 独自スキル名のリスト。
    """

    name: str = "base"

    def __init__(
        self,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.brand_dna = brand_dna
        self.skills = skills or []
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Anthropic クライアントを遅延生成して返す。

        SDK 未インストール環境でもモジュール import を妨げないよう遅延 import。
        """
        if self._client is None:
            from anthropic import Anthropic  # 遅延 import

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """エージェントのメイン処理。各エージェントが実装する。"""
        ...

    @abstractmethod
    def acceptance_gate(self, output: dict[str, Any]) -> GateResult:
        """このステージの「合格ゲート(テストスイート相当)」。

        機械判定可能な合格基準を返す。基準を定義できない工程は自律化しない
        (設計原則 第二条)。
        """
        ...

    def authorize(self, action: str) -> GateResult:
        """この行為が自分の許可スコープ内かを決定論ゲートで確認する。"""
        return permission_scope_gate(self.name, action)

    def call_llm(self, system: str, messages: list[dict[str, Any]]) -> str:
        """LLM 呼び出しの共通処理(Anthropic SDK 経由)。"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        return response.content[0].text
