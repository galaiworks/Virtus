"""シグナル層(§12-3 / §3)。

成否の 80-90% を占める本丸。外部データ連携と自前構築のどちらにも対応できる
アダプタ境界を定義する(`decisions.SignalLayerMode` で切替)。Phase 1 は外部連携で
立ち上げ、段階的に自前へ寄せられる設計。

幻覚リスク対策(§8.5):取得したシグナルは必ず実在性検証を通す。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.officina.decisions import SignalLayerMode


class SignalSource(ABC):
    """シグナル取得のアダプタ境界。"""

    mode: SignalLayerMode

    @abstractmethod
    def fetch(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """シグナル候補レコードを取得する。"""
        raise NotImplementedError

    def verify(self, record: dict[str, Any]) -> bool:
        """実在性検証(§8.5)。最低限、連絡先が到達可能形式であること。"""
        email = str(record.get("email", "")).strip()
        return bool(email) and "@" in email and "." in email.split("@")[-1]

    def fetch_verified(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """取得 → 実在性検証を通したレコードのみ返す。"""
        return [r for r in self.fetch(query) if self.verify(r)]


class IntegrationSignalSource(SignalSource):
    """外部データ連携(Clay 相当の API)。

    オフライン/テストでは ``fixtures`` をデータソースとして扱う。実運用では
    外部 API クライアントを差し込む。
    """

    mode = SignalLayerMode.INTEGRATION

    def __init__(self, fixtures: list[dict[str, Any]] | None = None) -> None:
        self._fixtures = fixtures or []

    def fetch(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        segment = query.get("segment")
        if segment is None:
            return list(self._fixtures)
        return [r for r in self._fixtures if r.get("segment") in (None, segment)]


class InHouseSignalSource(SignalSource):
    """自前シグナル構築(段階的に強化)。"""

    mode = SignalLayerMode.IN_HOUSE

    def __init__(self, store: list[dict[str, Any]] | None = None) -> None:
        self._store = store or []

    def fetch(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self._store)


def get_signal_source(
    mode: SignalLayerMode, data: list[dict[str, Any]] | None = None
) -> SignalSource:
    """方針に応じたシグナルソースを返す。

    HYBRID は Phase 1 では外部連携として振る舞う(段階的に自前へ寄せる)。
    """
    if mode == SignalLayerMode.IN_HOUSE:
        return InHouseSignalSource(data)
    return IntegrationSignalSource(data)
