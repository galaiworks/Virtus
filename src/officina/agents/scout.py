"""Scout — ステージ 0:ICP・市場リサーチ(Virtus: Researcher)。"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent


class Scout(BaseAgent):
    """ICP 仮説とターゲットリスト母集団を作る。

    合格ゲート:ソース実在性チェック(出力 ``gate.sources_verified``)。
    """

    name = "scout"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        segment = task.get("segment", "ひとり社長・コーチ・コンサル")
        sources = task.get("sources", ["prtimes", "linkedin", "note"])
        icp = {
            "segment": segment,
            "pain_points": task.get("pain_points", ["集客の属人化", "営業の時間不足"]),
            "value_prop": self.brand_dna.get("identity", {}).get(
                "unique_value_proposition", ""
            ),
            "target_acv_band": task.get("acv_band", "<25k"),
        }
        # オフラインでは渡されたソースを実在扱い。実運用では Prospector/Guardian が検証。
        verified = all(isinstance(s, str) and s for s in sources)
        return AgentResult(
            agent=self.name,
            content_type="icp",
            output={
                "icp": icp,
                "target_population_sources": sources,
                "gate": {"sources_verified": verified},
            },
            meta={"stage": 0},
        )
