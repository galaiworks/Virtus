"""判断の型(クロエの意思決定ロジック)。

`.claude/agents/incorporation-advisor.md` の「判断の型」を決定論的に実装する。
LLM に判断させず if/then で確定させることで、同じ入力に同じ結論を返す
(ガバナンス 3 層の §6.1 決定論ゲートと同じ思想)。

⚠️ すべての出力は「決断のための整理」であり確定的な税務・法務助言ではない。
各 advice は ``needs_expert`` を必ず立て、専門家確認とセットで提示させる。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: 消費税の免税を維持できる資本金の上限(円・未満であること)。
CAPITAL_EXEMPTION_LIMIT_JPY = 10_000_000

#: 極小資本とみなす閾値(円)。法人口座審査の難易度が跳ね上がる目安。
MICRO_CAPITAL_THRESHOLD_JPY = 500_000

#: 給与所得者の「20 万円ルール」(所得税の確定申告要否の目安)。
SIDE_INCOME_FILING_THRESHOLD_JPY = 200_000

#: 配偶者等の給与を扶養内に収める目安(いわゆる 103 万円の壁)。
SPOUSE_WALL_JPY = 1_030_000

#: 雇用関連助成金が対象外とする親族の範囲(親等)。
SUBSIDY_EXCLUDED_KINSHIP_DEGREE = 3


@dataclass
class Advice:
    """判断 1 件の出力。

    Attributes:
        topic: 判断項目(例 ``invoice``)。
        conclusion: 結論(1 行)。
        reasons: 根拠(数字・具体例つき)。
        warnings: 見落とすと損失につながる注意点。
        needs_expert: 専門家の最終確認が必要か(原則 True)。
        follow_up: 結論を確定させるために必要な追加情報。
    """

    topic: str
    conclusion: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    needs_expert: bool = True
    follow_up: list[str] = field(default_factory=list)


def invoice_advice(client_mix: str, *, capital_jpy: int | None = None) -> Advice:
    """インボイス(適格請求書)登録の要否を判断する。

    Args:
        client_mix: ``b2b`` | ``b2c`` | ``mixed``。取引先の主構成。
        capital_jpy: 資本金(円)。免税の前提(1,000 万円未満)確認に使う。

    Returns:
        ``Advice``。
    """
    mix = (client_mix or "").strip().lower()
    reasons: list[str] = []
    warnings: list[str] = []

    if capital_jpy is not None and capital_jpy >= CAPITAL_EXEMPTION_LIMIT_JPY:
        warnings.append(
            f"資本金 {capital_jpy:,} 円は 1,000 万円以上のため、"
            "そもそも新設法人の免税前提を満たさない"
        )

    if mix == "b2c":
        reasons.append("取引先が消費者・免税事業者中心で仕入税額控除を必要としない")
        reasons.append("新設法人は最大 2 期免税。登録すると免税のうまみを手放す純損")
        return Advice(
            topic="invoice",
            conclusion="登録しない(免税を維持する)",
            reasons=reasons,
            warnings=warnings
            + ["将来 B2B(課税事業者)比率が上がったら再判定する"],
            follow_up=["主要取引先の課税事業者比率を定期的に確認する"],
        )

    if mix == "b2b":
        reasons.append("取引先が課税事業者で、控除できないと実質値上げになり敬遠されうる")
        reasons.append("登録後も 2 割特例・簡易課税で納税負担を圧縮できる")
        return Advice(
            topic="invoice",
            conclusion="登録する(取引機会の損失を避ける)",
            reasons=reasons,
            warnings=warnings + ["登録した時点で課税事業者となり免税は終了する"],
            follow_up=["2 割特例・簡易課税の適用可否を税理士と確認する"],
        )

    return Advice(
        topic="invoice",
        conclusion="要確認(B2B 比率で判断が分かれる)",
        reasons=reasons + ["B2B と B2C が混在しており、控除ニーズの有無で結論が反転する"],
        warnings=warnings,
        follow_up=["売上に占める課税事業者向けの比率を数値で把握する"],
    )


def capital_advice(
    capital_jpy: int,
    *,
    needs_bank_account_soon: bool = False,
    virtual_office: bool = False,
) -> Advice:
    """資本金額の妥当性を判断する。

    Args:
        capital_jpy: 予定資本金(円)。
        needs_bank_account_soon: 設立直後に法人口座へ大型着金の予定があるか。
        virtual_office: 本店がバーチャルオフィスか。

    Returns:
        ``Advice``。
    """
    reasons: list[str] = []
    warnings: list[str] = []
    follow_up: list[str] = []

    if capital_jpy >= CAPITAL_EXEMPTION_LIMIT_JPY:
        warnings.append(
            "1,000 万円以上は設立初年度から課税事業者となり、2 期免税を失う"
        )
        conclusion = "1,000 万円未満へ引き下げる検討を推奨"
    else:
        reasons.append("1,000 万円未満のため消費税の免税前提と均等割の最低ラインを維持")
        conclusion = "妥当(免税の前提を満たす)"

    if capital_jpy < MICRO_CAPITAL_THRESHOLD_JPY:
        warnings.append(
            f"極小資本({capital_jpy:,} 円)は法人口座の開設審査で最も不利になりやすい"
        )
        reasons.append("設立費用は発起人立替→創立費・開業費、運転資金は役員借入金で回せる")
        follow_up.append("事業実態(契約書・請求書・HP・事業計画)を口座審査用に揃える")
        if virtual_office:
            warnings.append(
                "極小資本 × バーチャルオフィスは審査難易度が重なる"
                "(自治体の制度融資が使えない場合もある)"
            )
        if needs_bank_account_soon:
            warnings.append(
                "大型着金の予定があるため、着金より先に口座を開設できるか"
                "がクリティカルパスになる"
            )
            follow_up.append("設立直後に複数行へ並行申込する")

    return Advice(
        topic="capital",
        conclusion=conclusion,
        reasons=reasons,
        warnings=warnings,
        follow_up=follow_up,
    )


def officer_comp_advice(
    employment: str,
    *,
    living_cost_monthly_jpy: int = 0,
) -> Advice:
    """役員報酬の方針を判断する。

    Args:
        employment: ``full_time``(専業)| ``side``(本業を継続)。
        living_cost_monthly_jpy: 月あたりの必要生活費(手取り・円)。

    Returns:
        ``Advice``。
    """
    mode = (employment or "").strip().lower()
    warnings = [
        "定期同額給与は事業年度開始から 3 ヶ月以内に決定する(期中変更は損金不算入)"
    ]

    if mode == "side":
        return Advice(
            topic="officer_comp",
            conclusion="役員報酬を抑える(ゼロも選択肢)",
            reasons=[
                "本業給与があるため上乗せは所得税の累進と社会保険で不利になりやすい",
                "利益は法人に残し、軽減税率と各種繰延(共済等)を活かす",
            ],
            warnings=warnings,
            follow_up=["本業の就業規則で役員兼業が可能か確認する"],
        )

    if mode == "full_time":
        annual_net = living_cost_monthly_jpy * 12
        reasons = [
            "専業のため本業の社会保険が外れる。法人で社保に加入する土台が必要",
            "生活費を会社から取れないと役員貸付や経費処理に頼りグレーになる",
        ]
        follow_up: list[str] = []
        if annual_net > 0:
            # 税・社会保険で概ね 2〜3 割目減りする前提の概算レンジ。
            gross_low = int(annual_net / 0.8)
            gross_high = int(annual_net / 0.7)
            reasons.append(
                f"手取り年 {annual_net:,} 円を得るには額面 "
                f"{gross_low:,}〜{gross_high:,} 円が目安(概算)"
            )
        else:
            follow_up.append("必要生活費(月額・手取り)を確定する")
        return Advice(
            topic="officer_comp",
            conclusion="生活に必要な額を取り、それを超えて過剰には取らない(1 円はナシ)",
            reasons=reasons,
            warnings=warnings
            + ["退職日・設立日・社保加入日を連動させ、無保険の空白を作らない"],
            follow_up=follow_up + ["役員報酬の最適水準を税理士と確定する"],
        )

    return Advice(
        topic="officer_comp",
        conclusion="要確認(専業か兼業かで結論が反転する)",
        reasons=["本業を継続するか退職して専業かが決め手"],
        warnings=warnings,
        follow_up=["働き方(専業 / 兼業)を確定する"],
    )


def family_split_advice(
    family: list[dict[str, Any]] | None,
    *,
    planned_salary_jpy: int = 0,
) -> Advice:
    """家族への給与による所得分散を判断する。

    Args:
        family: 家族構成。各要素は ``relation`` / ``can_work_on`` / ``other_income`` を持つ。
        planned_salary_jpy: 予定年間給与(円)。壁の設計(A/B)判定に使う。

    Returns:
        ``Advice``。

    Notes:
        雇用関連助成金(キャリアアップ助成金等)は事業主の 3 親等以内の親族を
        対象外とするため、家族雇用と助成金は**併用できない**。この事実を
        必ず ``warnings`` に含める(設計レビュー A-1 の是正)。
    """
    members = family or []
    workers = [m for m in members if (m.get("can_work_on") or "").strip()]

    warnings = [
        "実態のない給与は架空人件費として否認される。"
        "「実際に働く → 正しく払う → 結果として分散」の順序を守る",
        f"雇用関連助成金(キャリアアップ助成金等)は事業主の "
        f"{SUBSIDY_EXCLUDED_KINSHIP_DEGREE} 親等以内の親族が対象外。"
        "家族雇用は節税の手段であって助成金の対象にはならない",
    ]

    if not workers:
        return Advice(
            topic="family_split",
            conclusion="現時点では分散を推奨しない(従事実態が確認できない)",
            reasons=["実際に担える業務が特定できていないため、給与の妥当性を説明できない"],
            warnings=warnings,
            follow_up=["家族が実際に担える業務と月あたりの稼働時間を洗い出す"],
        )

    reasons = [
        "給与所得控除を人数分使える(各人に最低 55 万円)",
        "累進税率の低い帯に分散でき、世帯合計の税負担が下がりうる",
        f"従事可能な家族: {', '.join(str(m.get('relation', '')) for m in workers)}",
    ]

    if planned_salary_jpy <= 0:
        return Advice(
            topic="family_split",
            conclusion="分散は有効(金額は従事実態に応じて設計)",
            reasons=reasons,
            warnings=warnings,
            follow_up=["従事内容に見合う年間給与額を決める(壁の設計 A/B)"],
        )

    if planned_salary_jpy <= SPOUSE_WALL_JPY:
        pattern = "A(控えめ分散)"
        detail = "扶養の範囲内。手続きが軽く、確実に経費化できる"
    else:
        pattern = "B(本格分散)"
        detail = (
            "分散効果は大きいが、本人も社会保険の加入対象になりコストが増える"
            "(その分、年金・健保は手厚くなる)"
        )

    reasons.append(f"年間給与 {planned_salary_jpy:,} 円 → パターン {pattern}:{detail}")

    return Advice(
        topic="family_split",
        conclusion=f"パターン {pattern} で分散する",
        reasons=reasons,
        warnings=warnings,
        follow_up=["給与額の妥当性(職務内容との対応)を税理士と確認する"],
    )


def side_income_filing_note(sales_jpy: int, expenses_jpy: int, is_employee: bool) -> Advice:
    """設立前に個人で発生した売上の申告要否を整理する(変数①)。

    Args:
        sales_jpy: 売上(円)。
        expenses_jpy: 必要経費(円)。
        is_employee: 給与所得者か。

    Returns:
        ``Advice``。
    """
    income = max(0, sales_jpy - expenses_jpy)
    if not is_employee:
        return Advice(
            topic="side_income",
            conclusion="要確認(給与所得者でないため 20 万円ルールは適用されない)",
            reasons=[f"所得 {income:,} 円。基礎控除等との関係で判定する"],
            follow_up=["他の所得と合算して申告要否を税理士と確認する"],
        )

    if income <= SIDE_INCOME_FILING_THRESHOLD_JPY:
        conclusion = "所得税の確定申告は不要の見込み(20 万円以下)"
    else:
        conclusion = "所得税の確定申告が必要の見込み(20 万円超)"

    return Advice(
        topic="side_income",
        conclusion=conclusion,
        reasons=[f"所得 = 売上 {sales_jpy:,} − 経費 {expenses_jpy:,} = {income:,} 円"],
        warnings=[
            "住民税の申告は 20 万円ルールの対象外。所得税が不要でも別途必要",
            "医療費控除やふるさと納税等で確定申告する場合は 20 万円ルールが消え、"
            "副業所得も全額申告対象になる",
        ],
        follow_up=["経費の集計を確定する"],
    )
