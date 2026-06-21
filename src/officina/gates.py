"""決定論ゲート層 — LLM に判断させてはいけないハードロジック。

Officina ガバナンス 3 層の第 1 層。設計原則 第五条の実装。

なぜ LLM に判断させないのか:
    LLM は確率的に振る舞う。送信上限を「今回だけ」破り、値引きを
    もっともらしく正当化し、未署名の契約を「実質合意済み」と解釈しうる。
    送信量・価格下限・契約トリガー・課金・本番デプロイ・権限スコープは、
    事業の生死と法的責任に直結する不可逆領域である。よってこれらは
    モデルの解釈に委ねず、if/then のハードロジックで強制する。

すべてのゲートは :class:`GateResult` を返す。``allowed`` が ``False`` の場合、
呼び出し側エージェントはその行為を実行してはならない。``severity`` が
``"critical"`` の場合は人間エスカレーション(escalation.md の Level 4 相当)。

このモジュールは外部依存を持たない。純粋関数として単体テスト可能であること。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

Severity = Literal["info", "minor", "major", "critical"]


class GateError(Exception):
    """ゲート入力が不正(必須フィールド欠落・型不一致等)な場合に送出。

    入力不正は「ブロック」ではなく「設計バグ」であり、握り潰さず失敗させる。
    フェイルセーフのため、判定不能なものを ``allowed=True`` にしてはならない。
    """


@dataclass(frozen=True)
class GateResult:
    """決定論ゲートの判定結果。

    Attributes:
        allowed: 行為を許可してよいか。``False`` なら実行禁止。
        reason: 判定理由(監査ログ・エスカレーション通知に使う人間可読文字列)。
        severity: 重大度。``"critical"`` は即時人間エスカレーション。
        gate: 判定を下したゲート名(監査用)。
        details: 判定に使った数値等の付随情報(監査・回帰テスト用)。
    """

    allowed: bool
    reason: str
    severity: Severity = "info"
    gate: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def raise_if_blocked(self) -> None:
        """ブロックされていれば :class:`PermissionError` を送出する補助メソッド。"""
        if not self.allowed:
            raise PermissionError(f"[{self.gate}] blocked: {self.reason}")


def _require(payload: dict[str, Any], *keys: str, gate: str) -> None:
    """``payload`` に必須キーが揃っているか検査し、欠落なら :class:`GateError`。"""
    missing = [k for k in keys if k not in payload]
    if missing:
        raise GateError(f"[{gate}] missing required fields: {missing}")


# --------------------------------------------------------------------------- #
# 1. deliverability_gate — 到達性健全性(事業継続条件)
# --------------------------------------------------------------------------- #

#: 到達性の上限閾値。これを超えたら送信を止める。deliverability.md と同期。
DELIVERABILITY_LIMITS = {
    "bounce_rate": 0.03,  # バウンス率 3% 超で危険
    "spam_complaint_rate": 0.001,  # スパム苦情率 0.1% 超で危険
    "min_domain_reputation": 70,  # ドメイン評価 70 未満で危険(0-100)
}


def deliverability_gate(metrics: dict[str, Any]) -> GateResult:
    """ドメイン/アカウントの到達性が健全かを判定する。

    撤退の主因はクロージング不全ではなく到達不全である。過剰自動送信で
    ドメイン評価が崩壊すると事業全体が止まる。deliverability は「機能」では
    なく「前提」であり、日次監視・最優先で守る。

    Args:
        metrics: 以下のキーを持つ辞書:
            ``bounce_rate`` (float, 0-1),
            ``spam_complaint_rate`` (float, 0-1),
            ``domain_reputation`` (int|float, 0-100)。

    Returns:
        GateResult: いずれかの指標が閾値を超えていれば ``allowed=False``。
        バウンス/苦情の悪化は ``critical``(即アウトリーチ監査トリガー)。

    Raises:
        GateError: 必須メトリクスが欠落している場合。
    """
    gate = "deliverability_gate"
    _require(metrics, "bounce_rate", "spam_complaint_rate", "domain_reputation", gate=gate)

    violations: list[str] = []
    severity: Severity = "info"

    if metrics["bounce_rate"] > DELIVERABILITY_LIMITS["bounce_rate"]:
        violations.append(
            f"バウンス率 {metrics['bounce_rate']:.3f} > 上限 {DELIVERABILITY_LIMITS['bounce_rate']}"
        )
        severity = "critical"
    if metrics["spam_complaint_rate"] > DELIVERABILITY_LIMITS["spam_complaint_rate"]:
        violations.append(
            f"スパム苦情率 {metrics['spam_complaint_rate']:.4f} > 上限 "
            f"{DELIVERABILITY_LIMITS['spam_complaint_rate']}"
        )
        severity = "critical"
    if metrics["domain_reputation"] < DELIVERABILITY_LIMITS["min_domain_reputation"]:
        violations.append(
            f"ドメイン評価 {metrics['domain_reputation']} < 下限 "
            f"{DELIVERABILITY_LIMITS['min_domain_reputation']}"
        )
        severity = "major" if severity != "critical" else severity

    if violations:
        return GateResult(
            allowed=False,
            reason="到達性低下のため送信停止: " + " / ".join(violations),
            severity=severity,
            gate=gate,
            details=dict(metrics),
        )
    return GateResult(
        allowed=True,
        reason="到達性は健全",
        gate=gate,
        details=dict(metrics),
    )


# --------------------------------------------------------------------------- #
# 2. send_volume_gate — 送信量上限・ウォームアップ制御
# --------------------------------------------------------------------------- #

#: ドメイン年齢(日)に応じた 1 日あたり最大送信数(ウォームアップ曲線)。
WARMUP_CURVE = [
    (7, 20),  # 0-6 日目: 20 通/日
    (14, 50),  # 7-13 日目: 50 通/日
    (30, 150),  # 14-29 日目: 150 通/日
    (60, 400),  # 30-59 日目: 400 通/日
]
#: ウォームアップ完了後(60 日以降)の定常上限。
STEADY_STATE_DAILY_CAP = 1000


def _warmup_daily_cap(domain_age_days: int) -> int:
    """ドメイン年齢から当日の許容送信上限を返す(ウォームアップ曲線)。"""
    for threshold_days, cap in WARMUP_CURVE:
        if domain_age_days < threshold_days:
            return cap
    return STEADY_STATE_DAILY_CAP


def send_volume_gate(account_state: dict[str, Any], requested: int) -> GateResult:
    """要求された送信数が当日の上限を超えないかを判定する。

    ウォームアップ中の新規ドメインは少量から段階的に増やす。上限超過分は
    ブロックする(部分許可はしない — 呼び出し側が ``allowed`` 数まで絞る)。

    Args:
        account_state: ``domain_age_days`` (int), ``sent_today`` (int) を含む辞書。
            任意で ``daily_cap_override`` (int) を指定すると上限を上書きできる
            (専用ツール連携時など。ただし安全側に min を取る)。
        requested: これから送りたい通数。

    Returns:
        GateResult: 当日累計が上限を超える要求はブロック。``details`` に
        ``cap`` / ``remaining`` を入れ、呼び出し側が安全に減量できるようにする。

    Raises:
        GateError: 必須フィールド欠落、または ``requested`` が負。
    """
    gate = "send_volume_gate"
    _require(account_state, "domain_age_days", "sent_today", gate=gate)
    if requested < 0:
        raise GateError(f"[{gate}] requested must be >= 0, got {requested}")

    curve_cap = _warmup_daily_cap(int(account_state["domain_age_days"]))
    override = account_state.get("daily_cap_override")
    cap = min(curve_cap, override) if override is not None else curve_cap

    sent_today = int(account_state["sent_today"])
    remaining = max(0, cap - sent_today)
    details = {"cap": cap, "sent_today": sent_today, "remaining": remaining, "requested": requested}

    if sent_today + requested > cap:
        return GateResult(
            allowed=False,
            reason=(
                f"送信量上限超過: 既送 {sent_today} + 要求 {requested} > 上限 {cap} "
                f"(残り送信可能 {remaining} 通)"
            ),
            severity="major",
            gate=gate,
            details=details,
        )
    return GateResult(allowed=True, reason="送信量は上限内", gate=gate, details=details)


# --------------------------------------------------------------------------- #
# 3. price_floor_gate — 価格ガードレール(下限・無断値引き禁止)
# --------------------------------------------------------------------------- #


def price_floor_gate(quote: dict[str, Any]) -> GateResult:
    """見積が価格下限を割っていないか、無断値引きがないかを判定する。

    価格下限割れと「承認なしの値引き」はブロックする。値引きには人間承認
    (``human_approved=True``)を必須とする。LLM が「商談を取るため」に
    勝手に値引きを正当化することを防ぐ。

    Args:
        quote: 以下を含む辞書:
            ``amount`` (数値, 提示額),
            ``floor`` (数値, 許容下限),
            任意で ``discount_rate`` (float, 0-1, 適用値引き率),
            ``human_approved`` (bool, 値引きの人間承認有無)。

    Returns:
        GateResult: 下限割れ、または承認なし値引きはブロック(``major``)。

    Raises:
        GateError: 必須フィールド欠落、または金額が負。
    """
    gate = "price_floor_gate"
    _require(quote, "amount", "floor", gate=gate)
    amount = quote["amount"]
    floor = quote["floor"]
    if amount < 0 or floor < 0:
        raise GateError(f"[{gate}] amount/floor must be >= 0")

    discount_rate = float(quote.get("discount_rate", 0.0))
    human_approved = bool(quote.get("human_approved", False))
    details = {"amount": amount, "floor": floor, "discount_rate": discount_rate}

    if amount < floor:
        return GateResult(
            allowed=False,
            reason=f"価格下限割れ: 提示 {amount} < 下限 {floor}",
            severity="major",
            gate=gate,
            details=details,
        )
    if discount_rate > 0 and not human_approved:
        return GateResult(
            allowed=False,
            reason=f"承認なしの値引き({discount_rate:.0%})は禁止。人間承認が必要",
            severity="major",
            gate=gate,
            details=details,
        )
    return GateResult(allowed=True, reason="価格ガードレール通過", gate=gate, details=details)


# --------------------------------------------------------------------------- #
# 4. contract_trigger_gate — 契約締結トリガー(人間署名イベントのみ)
# --------------------------------------------------------------------------- #

#: 契約締結を確定できる署名イベントの提供元(電子契約/決済)。
VALID_SIGNATURE_PROVIDERS = {"stripe", "docusign", "cloudsign", "manual_human"}


def contract_trigger_gate(event: dict[str, Any]) -> GateResult:
    """契約が「締結済み」と扱えるのは、人間の署名イベントが確認された時のみ。

    署名は法的に取り消せない不可逆行為であり、署名主体は常に人間。
    AI はこのゲートを ``True`` にできない — 検証可能な署名イベントが
    外部(電子契約/決済)から到達して初めて成立する。

    Args:
        event: 以下を含む辞書:
            ``signed`` (bool),
            ``signer_is_human`` (bool),
            ``provider`` (str, :data:`VALID_SIGNATURE_PROVIDERS` のいずれか),
            任意で ``signature_id`` (str, 監査証跡)。

    Returns:
        GateResult: 署名済み AND 署名者が人間 AND 正規プロバイダ の場合のみ
        ``allowed=True``。それ以外はブロック(``critical``)。

    Raises:
        GateError: 必須フィールド欠落。
    """
    gate = "contract_trigger_gate"
    _require(event, "signed", "signer_is_human", "provider", gate=gate)

    if not event["signed"]:
        return GateResult(False, "未署名の契約は締結扱いにできない", "critical", gate, dict(event))
    if not event["signer_is_human"]:
        return GateResult(
            False, "署名者が人間でない。AI は契約署名できない", "critical", gate, dict(event)
        )
    if event["provider"] not in VALID_SIGNATURE_PROVIDERS:
        return GateResult(
            False,
            f"不正な署名プロバイダ: {event['provider']}",
            "critical",
            gate,
            dict(event),
        )
    return GateResult(
        allowed=True,
        reason="人間署名による契約締結を確認",
        gate=gate,
        details={"signature_id": event.get("signature_id", "")},
    )


# --------------------------------------------------------------------------- #
# 5. billing_gate — 課金実行(契約締結に紐づく場合のみ)
# --------------------------------------------------------------------------- #


def billing_gate(contract_state: dict[str, Any]) -> GateResult:
    """課金を実行してよいかを判定する。

    課金は、:func:`contract_trigger_gate` を通過した契約に紐づく場合のみ
    実行できる。締結されていない/金額未確定の課金はブロックする。

    Args:
        contract_state: 以下を含む辞書:
            ``contract_signed`` (bool, contract_trigger_gate 通過済みか),
            ``amount`` (数値, 請求額 > 0),
            任意で ``already_billed`` (bool, 二重課金防止)。

    Returns:
        GateResult: 締結済み AND 金額正 AND 未課金 の場合のみ許可。
        二重課金は ``critical``。

    Raises:
        GateError: 必須フィールド欠落。
    """
    gate = "billing_gate"
    _require(contract_state, "contract_signed", "amount", gate=gate)
    details = {"amount": contract_state["amount"]}

    if not contract_state["contract_signed"]:
        return GateResult(False, "未締結契約への課金は禁止", "critical", gate, details)
    if contract_state.get("already_billed", False):
        return GateResult(False, "二重課金の防止: 既に課金済み", "critical", gate, details)
    if contract_state["amount"] <= 0:
        return GateResult(False, f"不正な請求額: {contract_state['amount']}", "major", gate, details)
    return GateResult(allowed=True, reason="課金トリガー成立", gate=gate, details=details)


# --------------------------------------------------------------------------- #
# 6. prod_deploy_gate — 本番デプロイ(全テスト通過 AND Guardian 合格)
# --------------------------------------------------------------------------- #


def prod_deploy_gate(test_results: dict[str, Any], guardian_verdict: str) -> GateResult:
    """成果物を本番デプロイしてよいかを判定する。

    Claude Code が無人マージできたのは「顧客テスト＝機械判定可能な合格基準」が
    あったから。本番デプロイは 全テスト通過 AND Guardian 合格 の両方を満たす
    場合のみ許可する。どちらか一方でも欠ければブロック。

    Args:
        test_results: ``total`` (int), ``passed`` (int) を含む辞書。
            任意で ``failed_tests`` (list[str])。
        guardian_verdict: Guardian の判定。``"APPROVED"`` のみ合格。

    Returns:
        GateResult: 全テスト通過 かつ guardian_verdict == "APPROVED" のみ許可。

    Raises:
        GateError: 必須フィールド欠落。
    """
    gate = "prod_deploy_gate"
    _require(test_results, "total", "passed", gate=gate)
    total = int(test_results["total"])
    passed = int(test_results["passed"])
    details = {
        "total": total,
        "passed": passed,
        "guardian_verdict": guardian_verdict,
        "failed_tests": test_results.get("failed_tests", []),
    }

    if total == 0:
        return GateResult(
            False, "テストが 0 件。合格基準なしの本番デプロイは禁止", "major", gate, details
        )
    if passed < total:
        return GateResult(
            False,
            f"テスト未通過 ({passed}/{total})。本番デプロイ不可",
            "major",
            gate,
            details,
        )
    if guardian_verdict != "APPROVED":
        return GateResult(
            False,
            f"Guardian 未承認 (verdict={guardian_verdict})。本番デプロイ不可",
            "major",
            gate,
            details,
        )
    return GateResult(
        allowed=True,
        reason=f"全テスト通過 ({passed}/{total}) ＋ Guardian 承認",
        gate=gate,
        details=details,
    )


# --------------------------------------------------------------------------- #
# 7. permission_scope_gate — ゼロトラスト最小権限
# --------------------------------------------------------------------------- #

#: 各エージェントに許可された行為スコープ(必要最小権限)。
AGENT_PERMISSIONS: dict[str, set[str]] = {
    "orchestrator": {"delegate", "read", "escalate"},
    "scout": {"read", "web_search"},
    "prospector": {"read", "enrich", "data_api"},
    "outreach": {"send"},  # 送信のみ。データ書込・課金・デプロイ不可
    "qualifier": {"read", "classify", "escalate"},
    "discovery": {"read", "write_requirements"},
    "proposer": {"read", "draft", "quote"},
    "closer": {"read", "draft"},  # 補助のみ。署名権限なし
    "architect": {"read", "design"},
    "builder": {"read", "write_code", "deploy_staging"},  # 本番DB書込・本番デプロイ不可
    "guardian": {"read", "evaluate"},
    "delivery": {"read", "handoff"},
    "ops_analyst": {"read", "bill", "monitor"},
}


def permission_scope_gate(agent: str, action: str) -> GateResult:
    """エージェントが要求する行為が許可スコープ内かを判定する(ゼロトラスト)。

    例: Outreach は ``send`` のみ。Builder は本番デプロイ(``deploy_prod``)不可。
    未知のエージェント/スコープ外の行為はブロックする(デフォルト拒否)。

    Args:
        agent: エージェント名(:data:`AGENT_PERMISSIONS` のキー)。
        action: 要求する行為。

    Returns:
        GateResult: 許可スコープに含まれる行為のみ ``allowed=True``。
        スコープ外・未知エージェントはブロック(``critical``)。
    """
    gate = "permission_scope_gate"
    allowed_actions = AGENT_PERMISSIONS.get(agent)
    if allowed_actions is None:
        return GateResult(
            False,
            f"未知のエージェント '{agent}'。デフォルト拒否",
            "critical",
            gate,
            {"agent": agent, "action": action},
        )
    if action not in allowed_actions:
        return GateResult(
            False,
            f"権限スコープ外: '{agent}' に '{action}' は許可されていない "
            f"(許可: {sorted(allowed_actions)})",
            "critical",
            gate,
            {"agent": agent, "action": action, "allowed": sorted(allowed_actions)},
        )
    return GateResult(
        allowed=True,
        reason=f"'{agent}' は '{action}' を実行可能",
        gate=gate,
        details={"agent": agent, "action": action},
    )
