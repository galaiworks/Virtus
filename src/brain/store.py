"""Brain 層 SQLite ストア.

Phase 1 実装: leads と audit_log のみ.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.prospecting.scoring import LeadScore

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    company TEXT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    published_at TEXT NOT NULL,
    score INTEGER NOT NULL,
    priority TEXT NOT NULL,
    breakdown TEXT NOT NULL,
    matched_industries TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    content_id TEXT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
"""


class BrainStore:
    """SQLite で動作する最小ストア."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "BrainStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def upsert_lead(self, source: str, lead: LeadScore) -> None:
        """同一 (source, source_id) があれば更新、なければ挿入.

        created_at は ON CONFLICT の更新対象に含めないため、初回挿入時の値が維持される.
        """
        now = _utcnow_iso()
        self.conn.execute(
            """
            INSERT INTO leads (
                source, source_id, company, title, url, description,
                published_at, score, priority, breakdown, matched_industries,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_id) DO UPDATE SET
                company = excluded.company,
                title = excluded.title,
                url = excluded.url,
                description = excluded.description,
                published_at = excluded.published_at,
                score = excluded.score,
                priority = excluded.priority,
                breakdown = excluded.breakdown,
                matched_industries = excluded.matched_industries,
                updated_at = excluded.updated_at
            """,
            (
                source,
                lead.release.source_id,
                lead.release.company,
                lead.release.title,
                lead.release.url,
                lead.release.description,
                lead.release.published_at.isoformat(),
                int(lead.score),
                lead.priority,
                json.dumps(lead.breakdown, ensure_ascii=False),
                json.dumps(list(lead.matched_industries), ensure_ascii=False),
                "new",
                now,
                now,
            ),
        )
        self.conn.commit()

    def top_leads(self, limit: int = 50, min_score: int = 60) -> list[dict[str, Any]]:
        """スコア順に上位を取得."""
        rows = self.conn.execute(
            """
            SELECT * FROM leads
            WHERE score >= ?
            ORDER BY score DESC, published_at DESC
            LIMIT ?
            """,
            (min_score, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count_leads(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]

    def log_audit(
        self,
        agent: str,
        action: str,
        payload: dict[str, Any],
        content_id: str | None = None,
    ) -> int:
        """監査ログを記録."""
        cur = self.conn.execute(
            """
            INSERT INTO audit_log (agent, action, content_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                agent,
                action,
                content_id,
                json.dumps(payload, ensure_ascii=False),
                _utcnow_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def recent_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "breakdown" in data and isinstance(data["breakdown"], str):
        data["breakdown"] = json.loads(data["breakdown"])
    if "matched_industries" in data and isinstance(data["matched_industries"], str):
        data["matched_industries"] = json.loads(data["matched_industries"])
    if "payload" in data and isinstance(data["payload"], str):
        data["payload"] = json.loads(data["payload"])
    return data
