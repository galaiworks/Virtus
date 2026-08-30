"""設立支援の状態を一元管理する(設計レビュー B-7)。

意思決定(D-1〜D-7)・助成金ウォッチリスト・締切・回収額台帳を **単一の真実**
として保持する。Markdown ドキュメント群は人間向けビューであり、機械可読な
真実はこの state に置く(ドキュメント間の記述ゆれを構造的に防ぐ)。

永続化はファイル拡張子で切り替える:
- ``.json``: 標準ライブラリのみ(既定)
- ``.yaml`` / ``.yml``: PyYAML が必要(dev 依存)

北極星指標(``docs/chloe-service-roadmap.md``):
**金銭価値回収額 = 獲得助成金 + 節税確定額 + 取りこぼし回避額**
``confirmed``(確定)と ``potential``(見込み)を必ず分離して集計する。
見込みを実績として報告しないための構造的な歯止め。
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

#: 回収額のカテゴリ(北極星指標の内訳)。
VALUE_CATEGORIES = ("grant", "tax_saving", "avoided_loss")

#: 回収額の確度。``potential`` は実績に合算しない。
VALUE_STATUSES = ("potential", "confirmed")


@dataclass
class Decision:
    """意思決定 1 件(D-1〜D-7 等)。

    Attributes:
        key: 識別子(例 ``D-2``)。
        title: 項目名(例 ``インボイス登録の要否``)。
        value: 決定内容。未確定なら空文字。
        confirmed: 確定済みか。
        rationale: 決定理由(監査用)。
        needs_expert: 専門家の最終確認が必要か。
        updated_at: 最終更新時刻(epoch 秒)。
    """

    key: str
    title: str
    value: str = ""
    confirmed: bool = False
    rationale: str = ""
    needs_expert: bool = False
    updated_at: float = field(default_factory=time.time)


@dataclass
class ValueEntry:
    """回収額台帳の 1 行(北極星指標の構成要素)。

    Attributes:
        category: ``grant`` | ``tax_saving`` | ``avoided_loss``。
        label: 内容(例 ``登録免許税の軽減(特定創業支援)``)。
        amount_jpy: 金額(円)。
        status: ``potential``(見込み)| ``confirmed``(確定)。
        source: 根拠(制度名・計算根拠)。
    """

    category: str
    label: str
    amount_jpy: int
    status: str = "potential"
    source: str = ""

    def __post_init__(self) -> None:
        if self.category not in VALUE_CATEGORIES:
            raise ValueError(f"category は {VALUE_CATEGORIES} のいずれか: {self.category}")
        if self.status not in VALUE_STATUSES:
            raise ValueError(f"status は {VALUE_STATUSES} のいずれか: {self.status}")


@dataclass
class IncorporationState:
    """1 顧客の設立支援状態。

    Attributes:
        customer_id: 顧客 ID。
        profile: 業種・地域・家族構成など判断の入力(``rules`` / ``grants`` が参照)。
        decisions: 意思決定の集合(key -> Decision)。
        watchlist: 監視中の助成金/補助金(key -> dict。``grants`` が読み書き)。
        value_ledger: 回収額台帳。
        notes: 自由記述の申し送り。
    """

    customer_id: str
    profile: dict[str, Any] = field(default_factory=dict)
    decisions: dict[str, Decision] = field(default_factory=dict)
    watchlist: dict[str, dict[str, Any]] = field(default_factory=dict)
    value_ledger: list[ValueEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # 意思決定
    # ------------------------------------------------------------------ #
    def set_decision(
        self,
        key: str,
        title: str,
        value: str,
        *,
        confirmed: bool = True,
        rationale: str = "",
        needs_expert: bool = False,
    ) -> Decision:
        """意思決定を記録・更新する。"""
        decision = Decision(
            key=key,
            title=title,
            value=value,
            confirmed=confirmed,
            rationale=rationale,
            needs_expert=needs_expert,
        )
        self.decisions[key] = decision
        return decision

    def pending_decisions(self) -> list[Decision]:
        """未確定の意思決定を返す。"""
        return [d for d in self.decisions.values() if not d.confirmed]

    # ------------------------------------------------------------------ #
    # 回収額台帳(北極星指標)
    # ------------------------------------------------------------------ #
    def add_value(self, entry: ValueEntry) -> ValueEntry:
        """回収額を台帳に追加する。"""
        self.value_ledger.append(entry)
        return entry

    def confirm_value(self, label: str) -> ValueEntry | None:
        """見込みの回収額を確定へ昇格させる。

        Args:
            label: 対象エントリの ``label``。

        Returns:
            昇格したエントリ。該当が無ければ ``None``。
        """
        for entry in self.value_ledger:
            if entry.label == label:
                entry.status = "confirmed"
                return entry
        return None

    def value_recovered(self, status: str = "confirmed") -> int:
        """北極星指標:金銭価値回収額の合計(円)。

        Args:
            status: ``confirmed``(既定・実績)か ``potential``(見込み)。
        """
        if status not in VALUE_STATUSES:
            raise ValueError(f"status は {VALUE_STATUSES} のいずれか: {status}")
        return sum(e.amount_jpy for e in self.value_ledger if e.status == status)

    def value_breakdown(self, status: str = "confirmed") -> dict[str, int]:
        """カテゴリ別の回収額内訳を返す。"""
        breakdown = {c: 0 for c in VALUE_CATEGORIES}
        for entry in self.value_ledger:
            if entry.status == status:
                breakdown[entry.category] += entry.amount_jpy
        return breakdown

    # ------------------------------------------------------------------ #
    # 永続化
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        """シリアライズ可能な dict へ変換する。"""
        return {
            "customer_id": self.customer_id,
            "profile": self.profile,
            "decisions": {k: asdict(v) for k, v in self.decisions.items()},
            "watchlist": self.watchlist,
            "value_ledger": [asdict(v) for v in self.value_ledger],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncorporationState:
        """dict から復元する。"""
        return cls(
            customer_id=data["customer_id"],
            profile=dict(data.get("profile", {})),
            decisions={
                k: Decision(**v) for k, v in (data.get("decisions") or {}).items()
            },
            watchlist=dict(data.get("watchlist", {})),
            value_ledger=[ValueEntry(**v) for v in data.get("value_ledger", [])],
            notes=list(data.get("notes", [])),
        )

    def save(self, path: str | Path) -> Path:
        """ファイルへ保存する(拡張子で JSON / YAML を切り替え)。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        if path.suffix in {".yaml", ".yml"}:
            yaml = _require_yaml()
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
        else:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return path

    @classmethod
    def load(cls, path: str | Path) -> IncorporationState:
        """ファイルから読み込む(拡張子で JSON / YAML を切り替え)。"""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            yaml = _require_yaml()
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return cls.from_dict(data)


def _require_yaml() -> Any:
    """PyYAML を遅延 import する(未導入なら明示的に失敗させる)。"""
    try:
        import yaml  # noqa: PLC0415 - 任意依存のため遅延 import
    except ImportError as exc:  # pragma: no cover - 依存が無い環境のみ
        raise RuntimeError(
            "YAML で保存/読込するには PyYAML が必要です。"
            "`pip install pyyaml` するか .json 拡張子を使ってください。"
        ) from exc
    return yaml
