"""リジェクトログ = リグレッションテスト(設計原則 #6 / 要件定義 §2-6)。

人間・Guardian がゲートで弾いた事例を永続化し、回帰テスト化してドリフトを抑える。
過去に弾かれたパターンが再出現していないかを後続生成物に対して照合する。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from src.officina.models import RejectLogEntry, Stage


class RejectLog:
    """リジェクト事例の永続化と回帰チェック。

    Args:
        path: JSONL 保存先。``None`` ならインメモリのみ(テスト向け)。
    """

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path) if path else None
        self._entries: list[RejectLogEntry] = []
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                self._entries.append(RejectLogEntry.from_dict(json.loads(line)))

    def record(self, entry: RejectLogEntry) -> RejectLogEntry:
        """リジェクト 1 件を記録し永続化する。"""
        self._entries.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        return entry

    def entries(self, stage: Stage | None = None) -> list[RejectLogEntry]:
        if stage is None:
            return list(self._entries)
        return [e for e in self._entries if e.stage == stage]

    def check_regression(self, content: str, stage: Stage | None = None) -> list[RejectLogEntry]:
        """過去に弾かれたパターンが ``content`` に再出現していないか照合する。

        Returns:
            再出現を検出したリジェクト事例のリスト(空なら回帰なし=合格)。
        """
        hits: list[RejectLogEntry] = []
        for e in self.entries(stage):
            for tag in e.pattern_tags:
                if tag and tag in content:
                    hits.append(e)
                    break
        return hits

    def as_regression_suite(self) -> list[dict[str, list[str]]]:
        """蓄積した事例を回帰テストスイート形式で書き出す。"""
        return [
            {"id": [e.id], "stage": [e.stage.name], "must_not_contain": e.pattern_tags}
            for e in self._entries
            if e.pattern_tags
        ]

    def __len__(self) -> int:
        return len(self._entries)
