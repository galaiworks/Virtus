"""ゼロトラスト権限スコープ(要件定義 §6.1)。

各エージェントは必要最小スコープのみを持つ。
例:Outreach は送信のみ、Builder は本番 DB 書込不可。
LLM の解釈に委ねず、if/then のハードロジックで強制する。
"""

from __future__ import annotations

#: エージェント名 -> 許可アクション集合。
#: ここに無いアクションはすべて拒否(デフォルト deny)。
SCOPES: dict[str, set[str]] = {
    "orchestrator": {"delegate", "read_all", "aggregate"},
    "scout": {"web_search", "read_signals"},
    "prospector": {"web_search", "read_signals", "enrich", "verify_contact"},
    # アウトリーチは「送信のみ」。連絡先の取得・削除権限は持たない。
    "outreach": {"send_email", "send_dm", "read_sequence"},
    "qualifier": {"read_inbox", "classify", "escalate"},
    "discovery": {"read_meeting", "extract_requirements"},
    "proposer": {"draft_proposal", "compute_quote", "read_requirements"},
    "closer": {"draft_rebuttal", "organize_terms"},  # 補助のみ。署名権限なし
    "architect": {"design", "read_requirements"},
    # Builder は実装はできるが本番 DB 書込・本番デプロイはできない。
    "builder": {"write_code", "run_tests", "read_repo"},
    "guardian": {"read_all", "evaluate", "run_tests", "escalate"},
    "delivery": {"handover", "configure", "smoke_test"},
    "ops": {"create_invoice", "collect_payment", "monitor", "draft_upsell"},
    "analyst": {"read_all", "analyze", "monitor_drift"},
}

#: 誰も自律実行してはならない不可逆アクション(人間ゲート専用)。
HUMAN_ONLY_ACTIONS: set[str] = {
    "sign_contract",  # ゲート A:契約署名(法的・不可逆)
    "approve_delivery",  # ゲート B:納品物 最終承認(賠償リスク・不可逆)
    "write_prod_db",  # 本番 DB 書込
    "deploy_prod",  # 本番デプロイ
}


class PermissionDenied(PermissionError):
    """権限スコープ違反。"""


def check_permission(agent: str, action: str) -> bool:
    """``agent`` が ``action`` を実行できるかを返す(副作用なし)。"""
    if action in HUMAN_ONLY_ACTIONS:
        return False
    return action in SCOPES.get(agent, set())


def enforce_permission(agent: str, action: str) -> None:
    """権限が無ければ ``PermissionDenied`` を送出する。"""
    if not check_permission(agent, action):
        if action in HUMAN_ONLY_ACTIONS:
            raise PermissionDenied(
                f"'{action}' は人間専用の不可逆アクションです。"
                f"エージェント '{agent}' は実行できません。"
            )
        raise PermissionDenied(
            f"エージェント '{agent}' は '{action}' の権限を持ちません(ゼロトラスト)。"
        )
