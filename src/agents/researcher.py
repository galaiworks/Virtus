"""Researcher Agent - Trend research and competitor monitoring."""

import json
from typing import Any

from ..skills import format_brand_dna
from .base import BaseAgent


class Researcher(BaseAgent):
    """Researcher - trend, competitor, and keyword research."""

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="claude-sonnet-4-6",
            brand_dna=brand_dna,
            skills=skills or [],
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a research task."""
        task_type = task.get("task_type", "")
        context = task.get("context", {})

        if task_type == "trend_research":
            return self.trend_research(context)
        elif task_type == "competitor_watch":
            return self.competitor_watch(context)
        elif task_type == "keyword_research":
            return self.keyword_research(context)
        elif task_type == "summarize_sources":
            return self.summarize_sources(context)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def trend_research(self, context: dict[str, Any]) -> dict[str, Any]:
        """Research industry trends from provided source materials."""
        target_keywords = context.get("target_keywords", [])
        source_materials = context.get("source_materials", [])
        period = context.get("period", "直近7日")

        system = self._system_prompt(target_keywords, context.get("competitors", []))
        prompt = f"""以下のソース資料から、業界トレンドを抽出してください。

# 対象キーワード
{", ".join(target_keywords)}

# 期間
{period}

# ソース資料
{json.dumps(source_materials, ensure_ascii=False, indent=2)}

# 出力形式
```
【業界トレンド ({period})】

1. [トレンド名]
   - 概要: [1-2文]
   - 影響度: 高/中/低
   - ソース: [URL]
   - 顧客への意味: [ブランドDNAに照らした解釈]

【顧客への提言】
- [Lead Strategist への戦略インプット]
```

重要: ソース資料にない情報を捏造しないこと。各トレンドにソースURLを必ず付ける。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )

        return {
            "task_type": "trend_research",
            "success": True,
            "output": {"content": response, "period": period},
        }

    def competitor_watch(self, context: dict[str, Any]) -> dict[str, Any]:
        """Monitor competitor moves from provided sources."""
        competitors = context.get("competitors", [])
        source_materials = context.get("source_materials", [])

        system = self._system_prompt([], competitors)
        prompt = f"""競合の動きを分析してください。

# 競合リスト
{", ".join(competitors)}

# ソース資料（プレスリリース、SNS投稿、ニュース等）
{json.dumps(source_materials, ensure_ascii=False, indent=2)}

# 出力形式（JSON）
{{
  "competitor_moves": [
    {{
      "competitor": "競合A",
      "move": "新製品リリース、料金改定など",
      "source": "URL",
      "implication": "顧客への影響",
      "recommended_response": "対応策"
    }}
  ],
  "strategic_implications": "全体的な示唆"
}}"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {"raw": response}
        except json.JSONDecodeError:
            data = {"raw": response}

        return {
            "task_type": "competitor_watch",
            "success": True,
            "output": data,
        }

    def keyword_research(self, context: dict[str, Any]) -> dict[str, Any]:
        """Suggest SEO keyword opportunities."""
        seed_keywords = context.get("seed_keywords", [])
        existing_content_topics = context.get("existing_topics", [])

        system = self._system_prompt(seed_keywords, [])
        prompt = f"""SEO キーワード戦略を提案してください。

# シードキーワード
{", ".join(seed_keywords)}

# 既存コンテンツのトピック
{", ".join(existing_content_topics)}

# 出力形式（JSON）
{{
  "keyword_opportunities": [
    {{
      "keyword": "メインキーワード",
      "related": ["関連語1", "関連語2"],
      "estimated_difficulty": "low|medium|high",
      "search_intent": "情報収集|比較検討|購入意図",
      "content_recommendation": "推奨するコンテンツ形式"
    }}
  ],
  "topic_clusters": [
    {{"cluster_name": "...", "pillar_topic": "...", "supporting_topics": ["..."]}}
  ]
}}

注意: 推測値であり、SEOツールの実数値ではないことを明示。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {"raw": response}
        except json.JSONDecodeError:
            data = {"raw": response}

        return {
            "task_type": "keyword_research",
            "success": True,
            "output": data,
        }

    def summarize_sources(self, context: dict[str, Any]) -> dict[str, Any]:
        """Summarize a batch of source documents."""
        sources = context.get("sources", [])
        focus = context.get("focus", "")

        system = self._system_prompt([], [])
        prompt = f"""以下のソース資料を、{focus}の観点から要約してください。

# ソース
{json.dumps(sources, ensure_ascii=False, indent=2)}

各ソースについて:
- 要点（3点以内）
- 引用すべきポイント（URL付き）
- 顧客にとっての意味

ハルシネーション禁止。ソースにない情報を追加しないこと。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )

        return {
            "task_type": "summarize_sources",
            "success": True,
            "output": {"content": response},
        }

    def _system_prompt(self, keywords: list[str], competitors: list[str]) -> str:
        """Build base system prompt."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "顧客")
        brand_dna_text = format_brand_dna(self.brand_dna)

        return f"""あなたは Virtus の Researcher エージェントです。

# あなたの使命
顧客 {customer_name} のビジネス領域に関する情報を継続的に収集し、
他エージェントが活用できる形で整理することです。

# 顧客のブランドDNA
{brand_dna_text}

# 対象キーワード
{", ".join(keywords)}

# 競合リスト
{", ".join(competitors)}

# 守るべき原則

第一に、ハルシネーション禁止。
すべての情報にはソースURLを必ず付ける。

第二に、ブランドDNAに合致する情報のみ抽出。
顧客のターゲット層に関係ない情報は混入させない。

第三に、決済権者特定時はLinkedIn等の公開情報のみ使用。
個人情報の不正取得は絶対禁止。

第四に、著作権法遵守。引用は要約のみ、全文転載禁止。"""
