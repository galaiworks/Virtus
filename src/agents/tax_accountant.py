"""Tax Accountant — 税理士 AI エージェント(記帳補助・情報提供)。

⚠️ このエージェントは **税理士ではありません**。税務代理・税務書類の作成・
個別の税務相談は税理士の独占業務(税理士法第 52 条)であり、絶対に行いません。
依頼が独占業務に触れたら決定論的な境界ゲートで停止し、人間税理士へ回付します。

設計原則(CLAUDE.md 第四原則「規約遵守を絶対視する」/ 神さんの教え「逃げるな」):
- 独占業務境界ゲートは LLM の解釈に委ねず if/then のハードロジックで強制する。
- すべての出力に免責事項を付す。
- 税率・控除・期限の数値には根拠年度を添える(ハルシネーション対策)。
- オフライン(dry_run / API キー無し)でも決定論的に動作する。

詳細ルール: ``.claude/rules/tax-compliance.md``
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.agents.base import AgentResult, BaseAgent
from src.agents.tax_audit import TaxAuditEntry, TaxAuditLog

# --- 根拠年度(改正で変わる値は必ず年度を明示する) ---
SOURCE_YEAR = "令和6年度税制(2024年度)"

# --- 必須免責事項(tax-compliance.md §4) ---
DISCLAIMER = (
    "【免責】本内容は記帳・経理の一般的な情報提供および参考のための概算であり、"
    "税理士法上の税務相談・税務代理・税務書類の作成には当たりません。"
    "最終的な税務判断・申告は税理士または所轄税務署にご確認ください。"
)


# --- 独占業務境界ゲートのトリガー(tax-compliance.md §2) ---
#: 脱税・仮装隠蔽の幇助 -> 即・重大違反(Level 4・関与拒否)。
ILLEGAL_TRIGGERS: tuple[str, ...] = (
    "脱税",
    "所得を隠",
    "売上を隠",
    "売上を除外",
    "架空経費",
    "経費を水増し",
    "二重帳簿",
    "粉飾",
)

#: 税務代理・税務書類の作成 -> 独占業務(Level 3)。
FILING_TRIGGERS: tuple[str, ...] = (
    "申告書を作",
    "申告書の作成",
    "申告書を提出",
    "確定申告を代行",
    "確定申告書を作",
    "決算書を作",
    "決算書の作成",
    "税務署に提出",
    "税務署へ提出",
    "e-tax で提出",
    "etax で提出",
    "代わりに申告",
    "修正申告",
    "更正の請求",
    "青色申告決算書を作",
    "年末調整をやって",
    "年末調整を代行",
    "届出書を提出",
)

#: 税務調査・不服申立て -> 独占業務(Level 3)。
DISPUTE_TRIGGERS: tuple[str, ...] = (
    "税務調査",
    "調査の立会い",
    "調査の立ち会い",
    "税務署とやり取り",
    "税務署と交渉",
    "不服申立て",
    "異議申立て",
    "審査請求",
)

#: 個別具体的な税務相談 -> 独占業務(Level 2)。
ADVICE_TRIGGERS: tuple[str, ...] = (
    "私の場合",
    "私のこの",
    "うちの会社は",
    "この控除は使え",
    "経費で落とせますか",
    "経費で落ちますか",
    "経費にできますか",
    "節税してください",
    "節税策を教え",
    "いくら税金がかかりますか",
    "いくら納めれば",
)


@dataclass
class BoundaryResult:
    """独占業務境界ゲートの判定結果。"""

    verdict: str  # "pass" / "escalate_to_zeirishi" / "critical_violation"
    level: int
    reason: str = ""
    matched: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"


def boundary_check(request_text: str) -> BoundaryResult:
    """依頼文を検査し、税理士独占業務への抵触を決定論的に判定する。

    Args:
        request_text: 顧客からの依頼文。

    Returns:
        ``BoundaryResult``。``pass`` 以外は処理を停止しエスカレーションする。
    """
    text = request_text or ""

    illegal = [t for t in ILLEGAL_TRIGGERS if t in text]
    if illegal:
        return BoundaryResult(
            verdict="critical_violation",
            level=4,
            reason="脱税・仮装隠蔽の幇助依頼(関与拒否・即時人間通知)",
            matched=illegal,
        )

    filing = [t for t in FILING_TRIGGERS + DISPUTE_TRIGGERS if t in text]
    if filing:
        return BoundaryResult(
            verdict="escalate_to_zeirishi",
            level=3,
            reason="税理士独占業務(税務代理・税務書類の作成・税務調査対応)",
            matched=filing,
        )

    advice = [t for t in ADVICE_TRIGGERS if t in text]
    if advice:
        return BoundaryResult(
            verdict="escalate_to_zeirishi",
            level=2,
            reason="個別具体的な税務相談は税理士独占業務(一般情報提供に留める)",
            matched=advice,
        )

    return BoundaryResult(verdict="pass", level=0)


# --- 記帳補助:勘定科目マッピング(キーワード -> 科目候補) ---
#: 上から順に評価し、最初に一致した科目を採用する。
EXPENSE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("電車", "タクシー", "新幹線", "バス", "交通", "ガソリン", "駐車", "航空券"), "旅費交通費"),
    (("接待", "取引先と", "会食", "手土産", "お中元", "お歳暮"), "接待交際費"),
    (("打ち合わせ", "会議", "カフェ", "喫茶", "ミーティング"), "会議費"),
    (("書籍", "本", "新聞", "雑誌", "kindle"), "新聞図書費"),
    (("セミナー", "研修", "講座", "スクール", "受講"), "研修費"),
    (("サーバー", "saas", "ドメイン", "クラウド", "サブスク", "ソフト", "ツール利用"), "通信費"),
    (("携帯", "スマホ", "インターネット", "wi-fi", "wifi", "郵送", "切手", "宅配"), "通信費"),
    (("文具", "事務用品", "ペン", "ノート", "プリンタ", "インク", "コピー用紙"), "消耗品費"),
    (("家賃", "オフィス", "コワーキング", "テナント", "レンタルスペース"), "地代家賃"),
    (("電気", "ガス", "水道", "光熱"), "水道光熱費"),
    (("広告", "出稿", "リスティング", "チラシ", "宣伝"), "広告宣伝費"),
    (("外注", "業務委託", "デザイン依頼", "ライティング依頼"), "外注費"),
    (("振込手数料", "決済手数料", "銀行手数料", "手数料"), "支払手数料"),
)

DEFAULT_ACCOUNT = "雑費"


def _detect_amount(text: str) -> int | None:
    """テキストから金額(円)を推定する。'1,200円' '3000' 等に対応。"""
    m = re.search(r"([0-9][0-9,]*)\s*円?", text.replace("，", ","))
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def categorize_expense(description: str, amount: int | None = None) -> dict[str, Any]:
    """経費の勘定科目候補を提示する(記帳補助・最終確定は顧客/税理士)。"""
    text = (description or "").lower()
    account = DEFAULT_ACCOUNT
    confidence = 0.4
    needs_review = True

    for keywords, acct in EXPENSE_RULES:
        if any(kw.lower() in text for kw in keywords):
            account = acct
            confidence = 0.85
            needs_review = False
            break

    if amount is None:
        amount = _detect_amount(description or "")

    note = ""
    if account == "接待交際費":
        note = "法人は交際費の損金算入に上限あり。飲食は 1 人 1 万円以下で会議費判定の余地。"
    elif account == DEFAULT_ACCOUNT:
        note = "科目を特定できませんでした。取引内容を具体化するか税理士にご確認ください。"

    return {
        "description": description,
        "amount": amount,
        "account_suggestion": account,
        "confidence": round(confidence, 2),
        "needs_review": needs_review,
        "note": note,
    }


# --- 所得税 速算表(令和6年度・分離課税等は考慮しない概算) ---
#: (課税所得の上限, 税率, 控除額)。上限 None は上限なし。
INCOME_TAX_BRACKETS: tuple[tuple[int | None, float, int], ...] = (
    (1_950_000, 0.05, 0),
    (3_300_000, 0.10, 97_500),
    (6_950_000, 0.20, 427_500),
    (9_000_000, 0.23, 636_000),
    (18_000_000, 0.33, 1_536_000),
    (40_000_000, 0.40, 2_796_000),
    (None, 0.45, 4_796_000),
)

#: 復興特別所得税(基準所得税額の 2.1%・2037 年まで)。
RECONSTRUCTION_TAX_RATE = 0.021


def estimate_income_tax(taxable_income: int) -> dict[str, Any]:
    """課税所得から所得税を概算する(参考値・確定値ではない)。

    Args:
        taxable_income: 課税所得(各種控除後の金額)。円。

    Returns:
        概算税額の内訳。確定申告額ではないことを ``disclaimer`` で明示。
    """
    if taxable_income < 0:
        taxable_income = 0

    rate = 0.0
    deduction = 0
    for upper, r, d in INCOME_TAX_BRACKETS:
        if upper is None or taxable_income <= upper:
            rate, deduction = r, d
            break

    base_tax = max(0, int(taxable_income * rate - deduction))
    reconstruction_tax = int(base_tax * RECONSTRUCTION_TAX_RATE)
    total = base_tax + reconstruction_tax

    return {
        "taxable_income": taxable_income,
        "applied_rate": rate,
        "bracket_deduction": deduction,
        "base_income_tax": base_tax,
        "reconstruction_tax": reconstruction_tax,
        "estimated_total_tax": total,
        "source_year": SOURCE_YEAR,
        "note": (
            "課税所得(控除後)に速算表を適用した概算です。"
            "住民税・事業税・社会保険料や分離課税・税額控除は含みません。"
            "確定値ではありません。"
        ),
    }


# --- 適格請求書(インボイス)記載事項チェック ---
#: 適格請求書の必須記載 6 項目(消費税法・インボイス制度)。
INVOICE_REQUIRED_FIELDS: tuple[tuple[str, str], ...] = (
    ("issuer_name", "発行事業者の氏名または名称"),
    ("registration_number", "登録番号(T+13 桁)"),
    ("transaction_date", "取引年月日"),
    ("description", "取引内容(軽減税率対象はその旨)"),
    ("tax_rate_amounts", "税率ごとに区分した対価の額および適用税率"),
    ("tax_amounts", "税率ごとに区分した消費税額等"),
    ("recipient_name", "交付を受ける事業者の氏名または名称"),
)

_REG_NUMBER_RE = re.compile(r"^T\d{13}$")


def check_invoice(invoice: dict[str, Any]) -> dict[str, Any]:
    """適格請求書の記載事項の有無を形式チェックする(事実確認のみ)。

    税額の正誤判定は行わない(独占業務のため)。記載項目の充足のみを確認する。
    """
    missing: list[str] = []
    for key, label in INVOICE_REQUIRED_FIELDS:
        value = invoice.get(key)
        if value in (None, "", []):
            missing.append(label)

    reg = str(invoice.get("registration_number", "")).strip().replace("-", "")
    reg_valid = bool(_REG_NUMBER_RE.match(reg))
    reg_issue = ""
    if invoice.get("registration_number") and not reg_valid:
        reg_issue = "登録番号の形式が不正です(正しくは T + 数字 13 桁)。"

    is_qualified = not missing and reg_valid

    return {
        "is_qualified_invoice": is_qualified,
        "missing_fields": missing,
        "registration_number_valid": reg_valid,
        "registration_number_issue": reg_issue,
        "note": (
            "記載事項の形式チェックのみを行いました。"
            "税額計算の正誤や仕入税額控除の可否判断は税理士にご確認ください。"
        ),
    }


def bookkeeping_summary(expenses: list[dict[str, Any]]) -> dict[str, Any]:
    """経費一覧を勘定科目別に集計する(月次記帳サマリー)。"""
    by_account: dict[str, dict[str, Any]] = {}
    total = 0
    review_count = 0

    for exp in expenses:
        cat = categorize_expense(
            exp.get("description", ""), exp.get("amount")
        )
        acct = cat["account_suggestion"]
        amount = cat["amount"] or 0
        total += amount
        if cat["needs_review"]:
            review_count += 1

        bucket = by_account.setdefault(acct, {"total": 0, "count": 0})
        bucket["total"] += amount
        bucket["count"] += 1

    return {
        "by_account": by_account,
        "total_amount": total,
        "entry_count": len(expenses),
        "needs_review_count": review_count,
        "note": "自動分類の集計です。科目の最終確定は税理士にご確認ください。",
    }


# --- 申告・納付期限テーブル(通常年・土日は翌平日にずれる) ---
#: (ラベル, 月, 日)。参考の目安であり、実際の期限は国税庁で確認する。
DEADLINES: tuple[tuple[str, int, int], ...] = (
    ("所得税の確定申告・納付", 3, 15),
    ("個人事業者の消費税の確定申告・納付", 3, 31),
    ("所得税の予定納税(第1期)", 7, 31),
    ("所得税の予定納税(第2期)", 11, 30),
)


def deadline_reminder(today_month: int, today_day: int) -> dict[str, Any]:
    """当月起点で、直近の申告・納付期限を残日数付きで提示する。"""
    items = []
    for label, m, d in DEADLINES:
        # 同年内の月日差でざっくり残日数(概算・年跨ぎは翌年扱い)。
        delta_days = (m - today_month) * 30 + (d - today_day)
        if delta_days < 0:
            delta_days += 365
        items.append(
            {
                "label": label,
                "date": f"{m:02d}/{d:02d} 頃",
                "days_left": delta_days,
            }
        )
    items.sort(key=lambda x: x["days_left"])
    return {
        "deadlines": items,
        "note": (
            "期限は目安です。土日祝で翌平日にずれます。"
            "正確な期日は国税庁・所轄税務署でご確認ください。"
        ),
    }


class TaxAccountant(BaseAgent):
    """税理士 AI エージェント(記帳補助・情報提供・書類整理・期限管理)。

    ⚠️ 税理士ではない。独占業務(税務代理・税務書類作成・個別税務相談)には
    絶対に踏み込まず、境界ゲートで検出したら人間税理士へエスカレーションする。
    """

    name = "tax_accountant"

    def __init__(
        self,
        model: str,
        brand_dna: dict[str, Any],
        api_key: str | None = None,
        skills: list[str] | None = None,
        dry_run: bool = False,
        audit_log: TaxAuditLog | None = None,
    ) -> None:
        super().__init__(
            model=model,
            brand_dna=brand_dna,
            api_key=api_key,
            skills=skills,
            dry_run=dry_run,
        )
        #: 監査ログ(tax-compliance.md §7)。``None`` なら記録しない。
        self.audit_log = audit_log

    def _audit(self, result: AgentResult) -> None:
        """判定結果を監査ログへ記録する(設定時のみ)。"""
        if self.audit_log is None:
            return
        out = result.output
        self.audit_log.record(
            TaxAuditEntry(
                agent=self.name,
                task_type=out.get("task_type", ""),
                boundary_verdict=out.get("boundary_verdict", ""),
                escalation_level=int(result.meta.get("escalation_level", 0)),
                disclaimer_attached=bool(result.meta.get("disclaimer_attached", False)),
                source_year=str(result.meta.get("source_year", "")),
            )
        )

    #: 対応タスク種別 -> ハンドラ。
    def execute(self, task: dict[str, Any]) -> AgentResult:
        """タスクを実行する。独占業務ゲートを最優先で通す。

        Args:
            task: ``{"type": ..., ...}``。``request_text`` があれば境界チェック対象。

        Returns:
            ``AgentResult``。境界に抵触した場合は ``content_type='escalation'``。
        """
        task_type = task.get("type", "")
        # 依頼文全体(自由記述)を境界ゲートに通す。type 別入力も連結して検査。
        request_text = " ".join(
            str(v)
            for v in (
                task.get("request_text"),
                task.get("description"),
                task.get("question"),
            )
            if v
        )
        boundary = boundary_check(request_text)

        result = self._build_result(task, task_type, boundary)
        self._audit(result)
        return result

    def _build_result(
        self, task: dict[str, Any], task_type: str, boundary: BoundaryResult
    ) -> AgentResult:
        """境界判定とハンドラ結果から AgentResult を組み立てる。"""
        if not boundary.passed:
            return self._escalate(task_type, boundary)

        handlers = {
            "categorize_expense": self._categorize_expense,
            "estimate_income_tax": self._estimate_income_tax,
            "check_invoice": self._check_invoice,
            "bookkeeping_summary": self._bookkeeping_summary,
            "deadline_reminder": self._deadline_reminder,
        }
        handler = handlers.get(task_type)
        if handler is None:
            return AgentResult(
                agent=self.name,
                content_type="error",
                output={
                    "error": f"未対応のタスク種別: {task_type!r}",
                    "supported": sorted(handlers),
                    "boundary_verdict": boundary.verdict,
                    "disclaimer": DISCLAIMER,
                },
                meta={"boundary_verdict": boundary.verdict, "disclaimer_attached": True},
            )

        result = handler(task)
        return AgentResult(
            agent=self.name,
            content_type="tax_support",
            output={
                "task_type": task_type,
                "result": result,
                "disclaimer": DISCLAIMER,
                "boundary_verdict": "pass",
            },
            meta={
                "escalation_level": 0,
                "disclaimer_attached": True,
                "source_year": SOURCE_YEAR,
            },
        )

    def _escalate(self, task_type: str, boundary: BoundaryResult) -> AgentResult:
        """独占業務抵触時のエスカレーション結果を組み立てる。"""
        if boundary.verdict == "critical_violation":
            message = (
                "ご依頼は脱税・所得の仮装隠蔽に該当するおそれがあり、"
                "対応できません。適正な申告について提携税理士にご相談ください。"
            )
        else:
            message = (
                "ご依頼は税理士の独占業務(税理士法第 52 条)に該当するため、"
                "本エージェントでは対応できません。提携税理士におつなぎします。"
            )
        return AgentResult(
            agent=self.name,
            content_type="escalation",
            output={
                "task_type": task_type,
                "boundary_verdict": boundary.verdict,
                "reason": boundary.reason,
                "matched_triggers": boundary.matched,
                "message": message,
                "disclaimer": DISCLAIMER,
            },
            meta={
                "escalation_level": boundary.level,
                "route_to": "human_zeirishi",
                "disclaimer_attached": True,
            },
        )

    # --- タスクハンドラ(いずれも決定論・オフライン動作) ---
    def _categorize_expense(self, task: dict[str, Any]) -> dict[str, Any]:
        return categorize_expense(task.get("description", ""), task.get("amount"))

    def _estimate_income_tax(self, task: dict[str, Any]) -> dict[str, Any]:
        return estimate_income_tax(int(task.get("taxable_income", 0)))

    def _check_invoice(self, task: dict[str, Any]) -> dict[str, Any]:
        return check_invoice(task.get("invoice", {}))

    def _bookkeeping_summary(self, task: dict[str, Any]) -> dict[str, Any]:
        return bookkeeping_summary(task.get("expenses", []))

    def _deadline_reminder(self, task: dict[str, Any]) -> dict[str, Any]:
        return deadline_reminder(
            int(task.get("today_month", 1)), int(task.get("today_day", 1))
        )
