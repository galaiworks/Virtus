"""税務判定の監査ログ(tax-compliance.md §7)。

「AI が税理士の独占業務に踏み込んでいないこと」を後から証明できるよう、
すべての境界判定・エスカレーション・免責付与を記録する。

- ファイルパスを渡すと JSONL(1 行 1 エントリ)で追記保存する。
- パス省略時はメモリ内(``entries``)に保持し、オフライン/テストで検証できる。
- タイムスタンプは注入可能(決定論テストのため)。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TaxAuditEntry:
    """監査ログ 1 エントリ(tax-compliance.md §7 の tax_audit_log_entry)。"""

    agent: str
    task_type: str
    boundary_verdict: str  # pass / escalate_to_zeirishi / critical_violation
    escalation_level: int
    disclaimer_attached: bool
    source_year: str
    timestamp: str = ""


class TaxAuditLog:
    """税務判定の追記型監査ログ。

    Args:
        path: JSONL 出力先。``None`` ならメモリ内のみ(``entries`` で参照)。
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.entries: list[dict[str, Any]] = []

    def record(
        self,
        entry: TaxAuditEntry | dict[str, Any],
        *,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """エントリを記録し、保存後の dict を返す。"""
        data = asdict(entry) if isinstance(entry, TaxAuditEntry) else dict(entry)
        if not data.get("timestamp"):
            data["timestamp"] = timestamp or datetime.now(timezone.utc).isoformat()

        self.entries.append(data)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        return data
