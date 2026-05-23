"""Researcher - 探索・調査・能動営業."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .base import AgentResult, BaseAgent


@dataclass
class Lead:
    """Lead data structure."""

    company_name: str
    decision_maker: str | None
    title: str | None
    source: str
    source_url: str
    context: str
    score_wealth: int
    score_authority: int
    score_pain: int

    @property
    def total_score(self) -> float:
        return (self.score_wealth + self.score_authority + self.score_pain) / 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_name": self.company_name,
            "decision_maker": self.decision_maker,
            "title": self.title,
            "source": self.source,
            "source_url": self.source_url,
            "context": self.context,
            "score": {
                "wealth": self.score_wealth,
                "authority": self.score_authority,
                "pain": self.score_pain,
                "total": self.total_score,
            },
        }


class Researcher(BaseAgent):
    """
    Researcher エージェント (Sonnet 4.6)

    役割:
    - 業界トレンド継続調査
    - 競合動向監視
    - 検索キーワード調査
    - PRタイムズ毎日監視（能動営業ターゲット抽出）
    - X/LinkedInからの決済権者特定
    - 月次市場洞察レポート生成
    """

    name = "researcher"
    model_tier = "execution"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Researcher task."""
        task_type = task.get("type", "trend_research")

        handlers = {
            "trend_research": self.trend_research,
            "competitor_analysis": self.competitor_analysis,
            "lead_extraction": self.lead_extraction,
            "keyword_research": self.keyword_research,
            "market_insight": self.market_insight,
            "prospect_research": self.prospect_research,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def lead_extraction(self, task: dict[str, Any]) -> AgentResult:
        """
        PRタイムズ等からリード抽出（能動営業用）

        スコアリング基準:
        - 儲かってそう度（40点）: 売上記載、資金調達、採用増
        - 決済権あり度（30点）: 代表者名あり、小規模企業
        - 痛みがありそう度（30点）: 課題言及、業界マッチ
        """
        press_releases = task.get("press_releases", [])
        target_industries = task.get("target_industries", [])
        target_keywords = task.get("target_keywords", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたはPRタイムズ等のプレスリリースから、営業ターゲットを抽出・スコアリングします。

【スコアリング基準】

■ 儲かってそう度（0-40点）
- 売上/利益の記載あり: +15
- 資金調達発表: +15
- 採用強化/事業拡大: +10

■ 決済権あり度（0-30点）
- 代表者/役員名あり: +20
- 従業員50名以下: +10

■ 痛みがありそう度（0-30点）
- 課題/悩みの言及: +20
- ターゲット業界マッチ: +10

【出力フォーマット】
各リードを以下のJSON形式で出力してください:
{{
  "leads": [
    {{
      "company_name": "会社名",
      "decision_maker": "決済権者名（わかれば）",
      "title": "役職",
      "source": "PRTimes",
      "source_url": "URL",
      "context": "このリードが有望な理由",
      "score_wealth": 0-40,
      "score_authority": 0-30,
      "score_pain": 0-30
    }}
  ]
}}

スコア合計60点以上のリードのみ抽出してください。
"""

        pr_text = "\n\n---\n\n".join(
            [
                f"【{pr.get('title', 'No Title')}】\n{pr.get('content', '')}\nURL: {pr.get('url', '')}"
                for pr in press_releases
            ]
        )

        messages = [
            {
                "role": "user",
                "content": f"""以下のプレスリリースから営業ターゲットを抽出してください。

【ターゲット業界】
{', '.join(target_industries) if target_industries else '指定なし'}

【ターゲットキーワード】
{', '.join(target_keywords) if target_keywords else '指定なし'}

【プレスリリース一覧】
{pr_text if pr_text else 'プレスリリースデータなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)

            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(content[start:end])
                    leads = [Lead(**lead) for lead in data.get("leads", [])]
                else:
                    leads = []
            except json.JSONDecodeError:
                leads = []
                self.logger.warning("Failed to parse leads JSON")

            return AgentResult(
                success=True,
                content=[lead.to_dict() for lead in leads],
                metadata={
                    "type": "lead_extraction",
                    "count": len(leads),
                    "date": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(f"Lead extraction failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def trend_research(self, task: dict[str, Any]) -> AgentResult:
        """Research industry trends."""
        topics = task.get("topics", [])
        sources = task.get("sources", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたは業界トレンドを調査し、レポートを作成します。

レポートの構成:
1. 今日の注目トレンド TOP3
2. 各トレンドの詳細（何が起きているか、なぜ重要か）
3. 顧客のビジネスへの影響
4. 推奨アクション

すべての情報にはソースURLを付けてください。
ハルシネーション禁止：確認できない情報は書かない。
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のトピックについてトレンドレポートを作成してください。

【調査トピック】
{', '.join(topics) if topics else 'AI, マーケティング, ひとり社長'}

【情報ソース】
{', '.join(sources) if sources else '一般的なビジネスメディア'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "trend_research", "topics": topics},
            )
        except Exception as e:
            self.logger.error(f"Trend research failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def competitor_analysis(self, task: dict[str, Any]) -> AgentResult:
        """Analyze competitors."""
        competitors = task.get("competitors", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたは競合動向を分析します。

分析の観点:
1. 新サービス・機能リリース
2. 価格変更
3. マーケティング施策
4. 採用動向
5. メディア露出

各情報にはソースを付けてください。
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の競合について分析してください。

【競合リスト】
{', '.join(competitors) if competitors else '情報なし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "competitor_analysis", "competitors": competitors},
            )
        except Exception as e:
            self.logger.error(f"Competitor analysis failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def keyword_research(self, task: dict[str, Any]) -> AgentResult:
        """Research SEO keywords."""
        seed_keywords = task.get("seed_keywords", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたはSEOキーワード調査を行います。

出力:
1. メインキーワード候補
2. 関連キーワード（ロングテール）
3. 検索意図の分析
4. コンテンツ企画提案
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のシードキーワードからキーワード調査を行ってください。

【シードキーワード】
{', '.join(seed_keywords) if seed_keywords else 'AIエージェント, ひとり社長, 集客自動化'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "keyword_research", "seed_keywords": seed_keywords},
            )
        except Exception as e:
            self.logger.error(f"Keyword research failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def market_insight(self, task: dict[str, Any]) -> AgentResult:
        """Generate monthly market insight report."""
        industry = task.get("industry", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたは月次市場洞察レポートを作成します。

レポート構成:
1. 市場概況
2. 主要トレンド
3. 競合動向サマリー
4. 機会と脅威
5. 推奨戦略方針
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の業界について市場洞察レポートを作成してください。

【対象業界】
{industry if industry else 'AIエージェント・マーケティング自動化'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "market_insight", "industry": industry},
            )
        except Exception as e:
            self.logger.error(f"Market insight failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def prospect_research(self, task: dict[str, Any]) -> AgentResult:
        """Research specific prospect before outreach."""
        company_name = task.get("company_name", "")
        decision_maker = task.get("decision_maker", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたは商談前の企業・人物リサーチを行います。

調査項目:
1. 企業概要（事業内容、規模、沿革）
2. 直近のニュース・プレスリリース
3. 決済権者のプロフィール
4. 推定される課題・ニーズ
5. 提案のフック（話の切り口）
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の企業・人物についてリサーチしてください。

【企業名】
{company_name}

【決済権者】
{decision_maker if decision_maker else '不明'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={
                    "type": "prospect_research",
                    "company": company_name,
                    "decision_maker": decision_maker,
                },
            )
        except Exception as e:
            self.logger.error(f"Prospect research failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def get_system_prompt(self) -> str:
        """Get Researcher specific system prompt."""
        return f"""あなたは Virtus の Researcher（探索専任）エージェントです。

あなたの役割:
- 業界トレンド継続調査
- 競合動向監視
- PRタイムズ等からの能動営業ターゲット抽出
- 決済権者特定
- 市場洞察レポート生成

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則:
- ハルシネーション禁止（全データはソース付き）
- 「儲かってそう」スコアリングを徹底
- 事実と推測を明確に区別
"""
