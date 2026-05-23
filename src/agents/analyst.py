"""Analyst - 分析・学習."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import AgentResult, BaseAgent


class Analyst(BaseAgent):
    """
    Analyst エージェント (Sonnet 4.6)

    役割:
    - GA4データ分析
    - Search Console分析
    - 各SNS反応データ集約
    - 勝ちパターン抽出
    - Brain層への学習データ蓄積
    """

    name = "analyst"
    model_tier = "execution"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Analyst task."""
        task_type = task.get("type", "performance_report")

        handlers = {
            "performance_report": self.generate_performance_report,
            "content_analysis": self.analyze_content_performance,
            "lead_analysis": self.analyze_lead_performance,
            "win_pattern_extraction": self.extract_win_patterns,
            "kpi_dashboard": self.generate_kpi_dashboard,
            "recommendation": self.generate_recommendations,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def generate_performance_report(self, task: dict[str, Any]) -> AgentResult:
        """Generate monthly performance report."""
        period = task.get("period", "monthly")
        data = task.get("data", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは{period}パフォーマンスレポートを作成します。

【レポート構成】
1. エグゼクティブサマリー
2. KPI達成状況（目標 vs 実績）
3. コンテンツパフォーマンス
4. リード獲得状況
5. 商談・成約状況
6. 勝ちパターン
7. 改善ポイント
8. 来期への提言
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のデータでパフォーマンスレポートを作成してください。

【期間】
{period}

【GA4データ】
{data.get('ga4', '情報なし')}

【SNSデータ】
{data.get('social', '情報なし')}

【リードデータ】
{data.get('leads', '情報なし')}

【商談データ】
{data.get('deals', '情報なし')}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={
                    "type": "performance_report",
                    "period": period,
                    "generated_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(f"Performance report generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def analyze_content_performance(self, task: dict[str, Any]) -> AgentResult:
        """Analyze content performance."""
        content_data = task.get("content_data", [])
        platform = task.get("platform", "all")

        system_prompt = f"""{self.get_system_prompt()}

あなたはコンテンツパフォーマンスを分析します。

【分析観点】
1. エンゲージメント率
2. リーチ/インプレッション
3. 保存・シェア数
4. コンバージョン貢献
5. 時間帯・曜日別傾向

【出力】
- パフォーマンスサマリー
- TOP5コンテンツ
- 改善が必要なコンテンツ
- 傾向分析
- 推奨アクション
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のコンテンツデータを分析してください。

【プラットフォーム】
{platform}

【コンテンツデータ】
{content_data if content_data else 'データなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "content_analysis", "platform": platform},
            )
        except Exception as e:
            self.logger.error(f"Content analysis failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def analyze_lead_performance(self, task: dict[str, Any]) -> AgentResult:
        """Analyze lead generation and conversion performance."""
        lead_data = task.get("lead_data", [])
        deal_data = task.get("deal_data", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたはリード・商談パフォーマンスを分析します。

【分析観点】
1. リードソース別の獲得数
2. リードスコア分布
3. 商談化率
4. 成約率
5. パイプライン健全性

【出力】
- ファネル分析
- 高パフォーマンスソース
- ボトルネック特定
- 改善提案
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のリード・商談データを分析してください。

【リードデータ】
{lead_data if lead_data else 'データなし'}

【商談データ】
{deal_data if deal_data else 'データなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "lead_analysis"},
            )
        except Exception as e:
            self.logger.error(f"Lead analysis failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def extract_win_patterns(self, task: dict[str, Any]) -> AgentResult:
        """Extract winning patterns from performance data."""
        content_data = task.get("content_data", [])
        outreach_data = task.get("outreach_data", [])
        deal_data = task.get("deal_data", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたは勝ちパターンを抽出します。

【パターン種別】
1. コンテンツパターン
   - 高エンゲージメントの要素
   - 効果的な構成・表現
2. アウトリーチパターン
   - 返信率が高いアプローチ
   - 効果的な件名・導入
3. クロージングパターン
   - 成約に至った要因
   - 効果的な提案構成

【出力形式】
各パターンについて:
- パターン名
- 詳細説明
- 成功事例
- 再現のためのポイント
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のデータから勝ちパターンを抽出してください。

【コンテンツデータ】
{content_data if content_data else 'データなし'}

【アウトリーチデータ】
{outreach_data if outreach_data else 'データなし'}

【商談データ】
{deal_data if deal_data else 'データなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={
                    "type": "win_pattern_extraction",
                    "extracted_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(f"Win pattern extraction failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def generate_kpi_dashboard(self, task: dict[str, Any]) -> AgentResult:
        """Generate KPI dashboard data."""
        kpi_targets = task.get("kpi_targets", {})
        current_data = task.get("current_data", {})

        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "metrics": [],
        }

        metrics_config = [
            ("content_published", "コンテンツ公開数", "本"),
            ("new_leads", "新規リード数", "件"),
            ("meetings_scheduled", "商談設定数", "件"),
            ("deals_closed", "成約数", "件"),
            ("revenue", "売上", "円"),
            ("engagement_rate", "エンゲージメント率", "%"),
        ]

        for key, label, unit in metrics_config:
            target = kpi_targets.get(key, 0)
            actual = current_data.get(key, 0)
            achievement = (actual / target * 100) if target > 0 else 0

            dashboard["metrics"].append({
                "key": key,
                "label": label,
                "target": target,
                "actual": actual,
                "unit": unit,
                "achievement_rate": round(achievement, 1),
                "status": "on_track" if achievement >= 80 else "at_risk" if achievement >= 50 else "off_track",
            })

        return AgentResult(
            success=True,
            content=dashboard,
            metadata={"type": "kpi_dashboard"},
        )

    def generate_recommendations(self, task: dict[str, Any]) -> AgentResult:
        """Generate strategic recommendations based on analysis."""
        analysis_data = task.get("analysis_data", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは分析結果に基づいて戦略的提言を行います。

【提言の構成】
1. 優先度HIGH（今すぐ実行）
2. 優先度MEDIUM（今月中に実行）
3. 優先度LOW（次月以降検討）

【各提言に含める情報】
- 提言内容
- 根拠（データに基づく）
- 期待される効果
- 実行ステップ
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の分析結果に基づいて戦略的提言を行ってください。

【分析結果】
{analysis_data if analysis_data else 'データなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "recommendations"},
            )
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def get_system_prompt(self) -> str:
        """Get Analyst specific system prompt."""
        return f"""あなたは Virtus の Analyst（分析・学習）エージェントです。

あなたの役割:
- GA4/Search Consoleデータ分析
- SNS反応データ集約
- 勝ちパターン抽出
- KPIダッシュボード生成
- 戦略提言

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則:
- データに基づく分析
- 具体的な数字を提示
- 実行可能な提言
- 傾向と原因の分析
"""
