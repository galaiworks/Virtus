"""リジェクトログ = リグレッションテスト(設計原則 #6)。"""

from __future__ import annotations

from src.officina.governance.reject_log import RejectLog
from src.officina.models import RejectLogEntry, Stage


def _entry(tag: str) -> RejectLogEntry:
    return RejectLogEntry(
        stage=Stage.PROPOSAL,
        agent="proposer",
        content=f"...{tag}...",
        reasons=[f"過剰約束: 「{tag}」"],
        pattern_tags=[tag],
    )


def test_record_and_regression_hit():
    log = RejectLog()
    log.record(_entry("絶対"))
    hits = log.check_regression("この提案は絶対に成功します")
    assert len(hits) == 1


def test_no_regression_when_pattern_absent():
    log = RejectLog()
    log.record(_entry("絶対"))
    assert log.check_regression("堅実で現実的な提案です") == []


def test_persistence_round_trip(tmp_path):
    path = tmp_path / "reject-log.jsonl"
    log = RejectLog(path)
    log.record(_entry("必ず"))
    # 別インスタンスで読み直しても回帰検出できる。
    reloaded = RejectLog(path)
    assert len(reloaded) == 1
    assert reloaded.check_regression("必ず儲かります")


def test_regression_suite_export():
    log = RejectLog()
    log.record(_entry("100%"))
    suite = log.as_regression_suite()
    assert suite and suite[0]["must_not_contain"] == ["100%"]
