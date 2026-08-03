"""助成金・補助金の適格性判定と週次モニタ(設計レビュー B-8)。

`docs/incorporation-grants-scan.md` の運用を実装する。

原則:
- **断定しない**。判定は ``LIKELY``(該当しそう)/ ``UNCERTAIN``(要確認)/
  ``EXCLUDED``(対象外)の 3 値で返し、可否の確定は専門家と一次情報に委ねる。
- **締切は逆算**してエスカレーション Level に接続する(``escalation`` モジュール)。
- 情報取得は公式ソース経由(無断スクレイピング禁止)。本モジュールは取得済み
  データの判定・管理に責務を限定する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class Eligibility(str, Enum):
    """適格性の 3 値判定。"""

    LIKELY = "likely"  # 該当しそう(それでも要確認)
    UNCERTAIN = "uncertain"  # 情報不足・要確認
    EXCLUDED = "excluded"  # 明確に対象外


class GrantStatus(str, Enum):
    """ウォッチリスト上の進捗。"""

    WATCHING = "watching"  # 公募待ち・監視中
    ELIGIBLE = "eligible"  # 該当しそう・未着手
    PREPARING = "preparing"  # 書類準備中
    APPLIED = "applied"  # 申請済
    ADOPTED = "adopted"  # 採択
    REJECTED = "rejected"  # 不採択
    CLOSED = "closed"  # 締切終了・見送り


@dataclass
class GrantProgram:
    """助成金/補助金 1 制度。

    Attributes:
        key: 識別子。
        name: 制度名。
        level: ``national`` | ``prefecture`` | ``city``。
        max_amount_jpy: 上限額(円)。0 は不定。
        deadline: 申請締切(``date``)。未定なら ``None``。
        deadline_confirmed: 締切を公式一次情報で確認済みか。
        requires_established: 申請に法人設立済みであることが必要か。
        excludes_relatives: 事業主の 3 親等以内の親族を対象外とするか。
        industries: 想定業種キーワード(空なら業種を問わない)。
        regions: 対象地域(空なら全国)。
        url: 公式ソース URL。
        notes: 補足(代替経路・注意点)。
    """

    key: str
    name: str
    level: str = "national"
    max_amount_jpy: int = 0
    deadline: date | None = None
    deadline_confirmed: bool = False
    requires_established: bool = True
    excludes_relatives: bool = False
    industries: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    url: str = ""
    notes: list[str] = field(default_factory=list)

    def days_until_deadline(self, today: date | None = None) -> int | None:
        """締切までの残日数。締切未定なら ``None``。"""
        if self.deadline is None:
            return None
        return (self.deadline - (today or date.today())).days


@dataclass
class EligibilityResult:
    """適格性判定 1 件の結果。"""

    program: GrantProgram
    eligibility: Eligibility
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    days_left: int | None = None

    @property
    def actionable(self) -> bool:
        """提案に値するか(対象外でなく、締切が残っている)。"""
        if self.eligibility == Eligibility.EXCLUDED:
            return False
        return self.days_left is None or self.days_left >= 0


def evaluate_eligibility(
    program: GrantProgram,
    profile: dict[str, Any],
    *,
    today: date | None = None,
) -> EligibilityResult:
    """プロフィールに対する 1 制度の適格性を判定する。

    Args:
        program: 対象制度。
        profile: ``industry`` / ``region`` / ``established`` / ``hiring_target`` 等。
        today: 判定基準日(テスト用に注入可能)。

    Returns:
        ``EligibilityResult``。断定を避け 3 値で返す。
    """
    reasons: list[str] = []
    warnings: list[str] = []
    excluded = False

    industry = str(profile.get("industry", ""))
    region = str(profile.get("region", ""))
    established = bool(profile.get("established", False))
    hiring_target = str(profile.get("hiring_target", ""))

    # --- 地域要件 ---
    if program.regions:
        if not region:
            warnings.append("所在地が未設定のため地域要件を判定できない")
        elif not any(r in region for r in program.regions):
            excluded = True
            reasons.append(f"地域要件({'/'.join(program.regions)})を満たさない")
        else:
            reasons.append(f"地域要件({region})を満たす")

    # --- 業種要件 ---
    if program.industries:
        if not industry:
            warnings.append("業種が未設定のため業種要件を判定できない")
        elif any(kw in industry for kw in program.industries):
            reasons.append(f"業種({industry})が対象領域に合致しそう")
        else:
            warnings.append(f"業種({industry})が想定領域と一致するか要確認")

    # --- 設立済み要件 ---
    if program.requires_established and not established:
        warnings.append("設立前は申請できない。設立後に着手する")

    # --- 親族除外(設計レビュー A-1) ---
    if program.excludes_relatives:
        warnings.append(
            "事業主の 3 親等以内の親族は対象外。家族雇用では使えず、"
            "外部スタッフの採用が前提"
        )
        if hiring_target == "family":
            excluded = True
            reasons.append("採用対象が家族のため対象外")

    # --- 締切 ---
    days_left = program.days_until_deadline(today)
    if days_left is not None:
        if days_left < 0:
            excluded = True
            reasons.append(f"締切({program.deadline})を過ぎている")
        else:
            reasons.append(f"締切まで残り {days_left} 日")
    if program.deadline is not None and not program.deadline_confirmed:
        warnings.append("締切が未確認。公式一次情報で確定してから動く")

    if excluded:
        eligibility = Eligibility.EXCLUDED
    elif warnings and not reasons:
        eligibility = Eligibility.UNCERTAIN
    elif reasons:
        eligibility = Eligibility.LIKELY
    else:
        eligibility = Eligibility.UNCERTAIN

    return EligibilityResult(
        program=program,
        eligibility=eligibility,
        reasons=reasons,
        warnings=warnings,
        days_left=days_left,
    )


def weekly_check(
    programs: list[GrantProgram],
    profile: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """週次モニタ 1 回分。該当候補を締切の近い順に並べて返す。

    Args:
        programs: 監視対象の制度一覧。
        profile: 顧客プロフィール。
        today: 判定基準日。

    Returns:
        ``candidates``(提案対象)/ ``excluded``(対象外)/ ``summary`` を含む dict。
    """
    results = [evaluate_eligibility(p, profile, today=today) for p in programs]
    candidates = [r for r in results if r.actionable]
    excluded = [r for r in results if not r.actionable]

    # 締切が近いものを先に。締切未定は後ろへ。
    candidates.sort(key=lambda r: (r.days_left is None, r.days_left if r.days_left is not None else 0))

    return {
        "checked_at": (today or date.today()).isoformat(),
        "candidates": [_result_to_dict(r) for r in candidates],
        "excluded": [_result_to_dict(r) for r in excluded],
        "summary": {
            "checked": len(results),
            "actionable": len(candidates),
            "excluded": len(excluded),
            "max_potential_jpy": sum(r.program.max_amount_jpy for r in candidates),
        },
    }


def _result_to_dict(result: EligibilityResult) -> dict[str, Any]:
    """判定結果を報告用 dict へ変換する。"""
    return {
        "key": result.program.key,
        "name": result.program.name,
        "level": result.program.level,
        "eligibility": result.eligibility.value,
        "max_amount_jpy": result.program.max_amount_jpy,
        "deadline": result.program.deadline.isoformat() if result.program.deadline else None,
        "days_left": result.days_left,
        "reasons": result.reasons,
        "warnings": result.warnings,
        "url": result.program.url,
        "notes": result.program.notes,
    }


def default_programs() -> list[GrantProgram]:
    """既定の監視対象(`docs/incorporation-grants-scan.md` の初回スキャン結果)。

    ⚠️ 締切・要件は毎年変動する。``deadline_confirmed=False`` の項目は
    公式一次情報で確定してから提示すること(設計レビュー A-3 の是正)。
    """
    return [
        GrantProgram(
            key="digital_ai",
            name="デジタル化・AI導入補助金(旧 IT 導入補助金)",
            level="national",
            industries=["AI", "ソフトウェア", "IT", "SaaS"],
            url="https://it-shien.smrj.go.jp/",
            notes=[
                "本命はベンダー側の IT 導入支援事業者登録"
                "(自社ツールを顧客が補助金で導入できる)",
                "新設法人は法人単独登録の経営基盤要件を満たせない場合がある。"
                "既存事業者のコンソーシアム構成員としての参加が代替経路",
            ],
        ),
        GrantProgram(
            key="jizokuka",
            name="小規模事業者持続化補助金",
            level="national",
            max_amount_jpy=500_000,
            url="https://www.chusho.meti.go.jp/",
            notes=[
                "HP 制作・広告・セミナー集客など販路開拓に使える",
                "商工会議所の事業支援計画書(様式 4)は申請締切より前に締め切られる",
            ],
        ),
        GrantProgram(
            key="monozukuri",
            name="ものづくり・商業・サービス生産性向上促進補助金",
            level="national",
            industries=["AI", "ソフトウェア", "システム"],
            url="https://portal.monodukuri-hojo.jp/",
            notes=["次回公募待ち。設備・システム開発など大型投資向け"],
        ),
        GrantProgram(
            key="career_up",
            name="キャリアアップ助成金(正社員化コース)",
            level="national",
            max_amount_jpy=1_400_000,
            excludes_relatives=True,
            url="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/part_haken/jigyounushi/career.html",
            notes=[
                "事業主の 3 親等以内の親族は対象外(家族雇用には使えない)",
                "計画書の事前認定が必要",
            ],
        ),
        GrantProgram(
            key="niigata_kigyo_challenge",
            name="起業チャレンジ応援事業(新潟県 / NICO)",
            level="prefecture",
            max_amount_jpy=2_000_000,
            regions=["新潟"],
            industries=["AI", "デジタル", "IT", "ソフトウェア"],
            requires_established=False,
            url="https://www.nico.or.jp/hojokin/",
            notes=[
                "デジタル技術で地域・社会課題を解決する起業が対象",
                "事前確認団体(商工会議所・金融機関)の確認書が必要",
            ],
        ),
        GrantProgram(
            key="niigata_tokutei_sogyo",
            name="特定創業支援等事業(新潟市)",
            level="city",
            max_amount_jpy=75_000,  # 登録免許税の軽減額(15 万 → 7.5 万)
            regions=["新潟"],
            requires_established=False,
            url="https://www.city.niigata.lg.jp/business/shoko/shokoshien/sogyoshien/sogyoshienn.html",
            notes=[
                "4 分野の支援を 4 回以上・1 ヶ月以上受ける必要がある",
                "証明書は設立登記より前に取得する必要がある(登録免許税が半額)",
            ],
        ),
    ]
