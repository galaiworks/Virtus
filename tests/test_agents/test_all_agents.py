"""Tests for all 8 Virtus agents and orchestrator."""

from unittest.mock import MagicMock

from src.agents import (
    Analyst,
    BaseAgent,
    Connector,
    Distributor,
    Drafter,
    Guardian,
    LeadStrategist,
    Researcher,
)

BRAND_DNA = {
    "identity": {"name": "TestBrand"},
    "voice": {
        "tone": "プロフェッショナル × 親近感",
        "vocabulary": {
            "preferred": ["率直に言うと", "結論から"],
            "avoid": ["絶対", "必ず"],
        },
        "signature_phrases": ["率直に言います"],
    },
    "forbidden": {
        "topics": ["競合のディスり", "政治的発言"],
        "expressions": ["絶対稼げる"],
    },
    "visual": {
        "colors": ["#1a1a2e", "#eaeaea"],
        "fonts": {"heading": "Noto Sans JP", "body": "Noto Sans JP"},
    },
}


def _mock_llm_response(text: str) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return response


class TestBaseAgent:
    """Tests for BaseAgent."""

    def test_brand_colors(self) -> None:
        class TestAgent(BaseAgent):
            def execute(self, task):
                return {}

        agent = TestAgent(api_key="test", model="claude-sonnet-4-6", brand_dna=BRAND_DNA)
        assert agent.get_brand_colors() == ["#1a1a2e", "#eaeaea"]

    def test_brand_fonts(self) -> None:
        class TestAgent(BaseAgent):
            def execute(self, task):
                return {}

        agent = TestAgent(api_key="test", model="claude-sonnet-4-6", brand_dna=BRAND_DNA)
        assert agent.get_brand_fonts()["heading"] == "Noto Sans JP"


class TestDrafter:
    """Tests for Drafter."""

    def test_init(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        assert drafter.model == "claude-sonnet-4-6"
        assert "garai-tone" in drafter.skills

    def test_extract_json_from_code_block(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        text = '```json\n{"title": "テスト"}\n```'
        result = drafter._extract_json(text)
        assert result == {"title": "テスト"}

    def test_extract_json_inline(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        text = 'これは結果です: {"key": "value"}'
        result = drafter._extract_json(text)
        assert result == {"key": "value"}

    def test_unknown_task_type_uses_generic(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        result = drafter.execute({"task_type": "unknown_type", "context": {}})
        assert result["success"] is False

    def test_write_note_article(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(
            return_value='{"title": "AIの未来", "content": "AIは...", "summary": "要約"}'
        )
        result = drafter.execute(
            {
                "task_type": "note_article",
                "context": {"topic": "AIの未来", "target_length": 2000},
            }
        )
        assert result["success"] is True
        assert "title" in result["output"]

    def test_write_x_post(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(return_value='[{"text": "テスト投稿", "hashtags": ["#AI"]}]')
        result = drafter.execute(
            {
                "task_type": "x_post",
                "context": {"topic": "AI活用", "thread_length": 1},
            }
        )
        assert result["success"] is True

    def test_write_outreach_email(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(
            return_value='{"subject": "件名", "body": "本文", "cta": "アクション"}'
        )
        result = drafter.execute(
            {
                "task_type": "outreach_email",
                "context": {"recipient_profile": {}, "purpose": "初回アプローチ"},
            }
        )
        assert result["success"] is True
        assert "subject" in result["output"]

    def test_write_proposal(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(
            return_value='{"title": "提案書", "sections": [{"title": "概要", "content": "..."}]}'
        )
        result = drafter.execute(
            {
                "task_type": "proposal",
                "context": {"client_name": "テスト社", "problem": "課題"},
            }
        )
        assert result["success"] is True

    def test_write_instagram_carousel(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(
            return_value='{"slides": [{"title": "スライド1", "content": "内容"}]}'
        )
        result = drafter.execute(
            {
                "task_type": "instagram_carousel",
                "context": {"topic": "AI入門", "slide_count": 5},
            }
        )
        assert result["success"] is True

    def test_write_youtube_script(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(
            return_value='{"title": "動画タイトル", "script": "台本...", "hook": "フック"}'
        )
        result = drafter.execute(
            {
                "task_type": "youtube_script",
                "context": {"topic": "AI解説", "target_duration": 600},
            }
        )
        assert result["success"] is True

    def test_refine(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        drafter.call_llm = MagicMock(return_value="改善されたコンテンツ")
        result = drafter.refine(
            content="元のコンテンツ",
            feedback="もっと具体的にしてください",
        )
        assert result == "改善されたコンテンツ"


class TestLeadStrategist:
    """Tests for LeadStrategist."""

    def test_init(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        assert ls.model == "claude-opus-4-7"

    def test_morning_brief(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        ls.call_llm = MagicMock(
            return_value="おはようございます、TestBrand さん。\n【今日の優先事項】\n1. ..."
        )
        result = ls.execute(
            {
                "task_type": "morning_brief",
                "context": {"current_date": "2026-05-23"},
            }
        )
        assert result["success"] is True
        assert "TestBrand" in result["output"]["content"]

    def test_weekly_review(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        ls.call_llm = MagicMock(
            return_value="【先週の成果】\n- リード獲得: 10件\n【勝ちパターン】\n..."
        )
        result = ls.execute(
            {
                "task_type": "weekly_review",
                "context": {
                    "week_data": {"leads": 10, "content": 5},
                    "previous_week_data": {"leads": 8, "content": 4},
                },
            }
        )
        assert result["success"] is True
        assert result["task_type"] == "weekly_review"

    def test_monthly_review(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        ls.call_llm = MagicMock(return_value="# 月次レビュー\n## KPI達成状況\n...")
        result = ls.execute(
            {
                "task_type": "monthly_review",
                "context": {
                    "month_data": {"leads": 40, "conversions": 5},
                    "targets": {"leads": 50, "conversions": 4},
                },
            }
        )
        assert result["success"] is True
        assert result["task_type"] == "monthly_review"

    def test_delegate_task(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        ls.call_llm = MagicMock(
            return_value='{"delegations": [{"agent": "Drafter", "task_type": "note_article"}], "execution_order": ["Drafter"]}'
        )
        result = ls.execute(
            {
                "task_type": "delegate_task",
                "context": {"goal": "AIエージェントについての記事を書く"},
            }
        )
        assert result["success"] is True
        assert "delegations" in result["output"]

    def test_delegate_task_invalid_json(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        ls.call_llm = MagicMock(return_value="{invalid json syntax")
        result = ls.execute(
            {
                "task_type": "delegate_task",
                "context": {"goal": "テスト"},
            }
        )
        assert result["success"] is True
        assert "raw_response" in result["output"]

    def test_unknown_task_type(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        result = ls.execute({"task_type": "unknown_type", "context": {}})
        assert "error" in result


class TestGuardian:
    """Tests for Guardian."""

    def test_init(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        assert guardian.model == "claude-opus-4-7"
        assert guardian.THRESHOLD == 95

    def test_unsubscribe_check_present(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        assert guardian._has_unsubscribe_link("配信停止はこちら: https://...")
        assert guardian._has_unsubscribe_link("解除リンク")

    def test_unsubscribe_check_missing(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        assert not guardian._has_unsubscribe_link("普通のメール本文だけ")

    def test_email_without_unsubscribe_fails(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        violations = guardian._check_legal_compliance(
            "営業メール本文だけ。送信者情報なし。", "outreach_email"
        )
        assert any(v.severity == "CRITICAL" for v in violations)

    def test_overpromise_detection(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        violations = guardian._check_overpromise("絶対に成功します。100%保証。")
        assert len(violations) >= 2
        assert all(v.severity == "MAJOR" for v in violations)

    def test_critical_violation_short_circuits(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        result = guardian.evaluate("営業メール本文だけ。送信者情報なし。", "outreach_email")
        assert result.verdict == "CRITICAL_VIOLATION"
        assert result.total_score == 0

    def test_parse_evaluation_coerces_string_score(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        evaluation = guardian._parse_evaluation('{"total_score": "96", "verdict": "APPROVED"}')
        assert evaluation.total_score == 96
        assert isinstance(evaluation.total_score, int)

    def test_parse_evaluation_invalid_score_defaults_zero(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        evaluation = guardian._parse_evaluation('{"total_score": "high", "verdict": "APPROVED"}')
        assert evaluation.total_score == 0

    def test_loop_respects_max_retries_override(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        guardian.call_llm = MagicMock(
            return_value='{"total_score": 80, "verdict": "REJECTED", "feedback_to_agent": "改善"}'
        )
        revise_calls = []

        def revise_fn(content: str, feedback: str) -> str:
            revise_calls.append(feedback)
            return content

        result = guardian.evaluate_with_loop(
            content="テスト",
            content_type="note_article",
            agent_name="Drafter",
            revise_fn=revise_fn,
            max_retries=1,
        )
        assert result["status"] == "escalated"
        assert result["reason"] == "max_retries_exceeded"
        assert len(revise_calls) == 2  # 初回 + リトライ1回


class TestResearcher:
    """Tests for Researcher."""

    def test_init(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        assert researcher.model == "claude-sonnet-4-6"

    def test_unknown_task(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        result = researcher.execute({"task_type": "unknown", "context": {}})
        assert "error" in result

    def test_trend_research(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        researcher.call_llm = MagicMock(
            return_value="【業界トレンド】\n1. AIエージェント\n- 概要: ..."
        )
        result = researcher.execute(
            {
                "task_type": "trend_research",
                "context": {
                    "target_keywords": ["AI", "エージェント"],
                    "source_materials": [{"url": "https://example.com", "content": "test"}],
                    "period": "直近7日",
                },
            }
        )
        assert result["success"] is True
        assert result["output"]["period"] == "直近7日"

    def test_competitor_watch(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        researcher.call_llm = MagicMock(
            return_value='{"competitor_moves": [{"competitor": "A社", "move": "新製品"}], "strategic_implications": "対策必要"}'
        )
        result = researcher.execute(
            {
                "task_type": "competitor_watch",
                "context": {
                    "competitors": ["A社", "B社"],
                    "source_materials": [{"url": "https://example.com"}],
                },
            }
        )
        assert result["success"] is True
        assert "competitor_moves" in result["output"]

    def test_competitor_watch_invalid_json(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        researcher.call_llm = MagicMock(return_value="不正なJSONレスポンス")
        result = researcher.execute(
            {
                "task_type": "competitor_watch",
                "context": {"competitors": ["A社"]},
            }
        )
        assert result["success"] is True
        assert "raw" in result["output"]

    def test_keyword_research(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        researcher.call_llm = MagicMock(
            return_value='{"keyword_opportunities": [{"keyword": "AI活用"}], "topic_clusters": []}'
        )
        result = researcher.execute(
            {
                "task_type": "keyword_research",
                "context": {
                    "seed_keywords": ["AI", "自動化"],
                    "existing_topics": ["マーケティング"],
                },
            }
        )
        assert result["success"] is True
        assert "keyword_opportunities" in result["output"]

    def test_keyword_research_invalid_json(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        researcher.call_llm = MagicMock(return_value="invalid json")
        result = researcher.execute(
            {
                "task_type": "keyword_research",
                "context": {"seed_keywords": ["test"]},
            }
        )
        assert result["success"] is True
        assert "raw" in result["output"]

    def test_summarize_sources(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        researcher.call_llm = MagicMock(return_value="# ソース要約\n## 1. Example\n- 要点: ...")
        result = researcher.execute(
            {
                "task_type": "summarize_sources",
                "context": {
                    "sources": [{"url": "https://example.com", "content": "test"}],
                    "focus": "AIトレンド",
                },
            }
        )
        assert result["success"] is True
        assert "content" in result["output"]


class TestDistributor:
    """Tests for Distributor."""

    def test_init(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        assert dist.model == "claude-haiku-4-5"

    def test_unapproved_content_rejected(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist.execute(
            {
                "task_type": "schedule_post",
                "context": {"approval_status": "pending"},
            }
        )
        assert "error" in result

    def test_compliance_x_length_check(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        long_text = "あ" * 300
        result = dist._check_platform_compliance("x", {"text": long_text})
        assert not result["passed"]

    def test_optimal_time_calculation(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist.execute(
            {
                "task_type": "calculate_optimal_time",
                "context": {"platform": "x"},
            }
        )
        assert result["success"]
        assert "optimal_time" in result["output"]

    def test_compliant_email_has_unsubscribe(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        email = dist._build_compliant_email(
            content={"subject": "Test", "body": "本文"},
            recipient={"email": "user@example.com"},
            sender_info={"company_name": "Test Co", "address": "東京", "phone": "03"},
        )
        assert "解除" in email["body"]
        assert "List-Unsubscribe" in email["headers"]

    def test_schedule_post_approved(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist.execute(
            {
                "task_type": "schedule_post",
                "context": {
                    "approval_status": "approved",
                    "platform": "note",
                    "content": {"title": "記事", "body": "本文"},
                    "scheduled_time": "2026-05-24T09:00:00+09:00",
                },
            }
        )
        assert result["success"] is True
        assert "scheduled" in result["output"]["status"]

    def test_compliance_note_check_passed(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist._check_platform_compliance("note", {"body": "短い本文"})
        assert result["passed"]

    def test_compliance_instagram_too_many_hashtags(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        hashtags = [f"#tag{i}" for i in range(35)]
        result = dist._check_platform_compliance(
            "instagram", {"caption": "素敵な写真", "hashtags": hashtags}
        )
        assert not result["passed"]

    def test_compliance_spam_pattern(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist._check_platform_compliance(
            "x", {"text": "フォローお願いします follow for follow"}
        )
        assert not result["passed"]

    def test_unknown_task_type(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist.execute({"task_type": "unknown", "context": {}})
        assert "error" in result


class TestConnector:
    """Tests for Connector."""

    def test_init(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        assert conn.model == "claude-sonnet-4-6"

    def test_escalation_level_4_keywords(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn._check_escalation_keywords("弁護士に相談します")
        assert result is not None
        assert result["level"] == 4

    def test_escalation_level_3_keywords(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn._check_escalation_keywords("クレームです")
        assert result is not None
        assert result["level"] == 3

    def test_no_escalation_for_normal(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        assert conn._check_escalation_keywords("こんにちは!") is None

    def test_dm_with_escalation(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.draft_dm_reply(
            {
                "incoming_message": {"text": "弁護士を立てます"},
                "sender_profile": {},
            }
        )
        assert result["output"]["escalation_required"] is True

    def test_follow_up_sequence(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.execute(
            {
                "task_type": "plan_follow_up",
                "context": {"sequence_type": "post_meeting"},
            }
        )
        actions = result["output"]["actions"]
        assert len(actions) == 4
        assert actions[0]["action"] == "thank_you"

    def test_dm_reply_normal(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        conn.call_llm = MagicMock(
            return_value='{"reply_draft": {"message": "ご連絡ありがとうございます!"}, "flag_for_attention": false}'
        )
        result = conn.execute(
            {
                "task_type": "draft_dm_reply",
                "context": {
                    "incoming_message": {"text": "サービスについて教えてください"},
                    "sender_profile": {"name": "テストユーザー"},
                },
            }
        )
        assert result["success"] is True
        assert "reply_draft" in result["output"]

    def test_comment_reply(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        conn.call_llm = MagicMock(return_value="コメントありがとうございます!")
        result = conn.execute(
            {
                "task_type": "draft_comment_reply",
                "context": {
                    "comment": {"text": "素晴らしい記事ですね"},
                    "post_context": {"title": "AI活用術"},
                },
            }
        )
        assert result["success"] is True

    def test_follow_up_post_purchase(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.execute(
            {
                "task_type": "plan_follow_up",
                "context": {"sequence_type": "post_purchase"},
            }
        )
        actions = result["output"]["actions"]
        assert any(a["action"] == "onboarding_help" for a in actions)

    def test_follow_up_no_reply(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.execute(
            {
                "task_type": "plan_follow_up",
                "context": {"sequence_type": "no_reply_first_outreach"},
            }
        )
        actions = result["output"]["actions"]
        assert any(a["action"] == "soft_reminder" for a in actions)

    def test_unknown_task_type(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.execute({"task_type": "unknown", "context": {}})
        assert "error" in result


class TestAnalyst:
    """Tests for Analyst."""

    def test_init(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        assert analyst.model == "claude-sonnet-4-6"

    def test_kpi_dashboard(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        result = analyst.execute(
            {
                "task_type": "kpi_dashboard",
                "context": {
                    "current_metrics": {
                        "content_volume": 35,
                        "lead_acquisition": 22,
                    },
                    "tier": 1,
                },
            }
        )
        assert result["success"]
        kpis = result["output"]["kpis"]
        assert kpis["content_volume"]["status"] == "達成"
        assert kpis["lead_acquisition"]["status"] == "達成"

    def test_kpi_status_thresholds(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        assert analyst._kpi_status(100) == "達成"
        assert analyst._kpi_status(85) == "順調"
        assert analyst._kpi_status(60) == "要注意"
        assert analyst._kpi_status(30) == "未達"

    def test_weekly_summary(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        analyst.call_llm = MagicMock(return_value="# 週次サマリー\n## パフォーマンス\n...")
        result = analyst.execute(
            {
                "task_type": "weekly_summary",
                "context": {
                    "week_data": {"posts": 10, "engagement": 500},
                },
            }
        )
        assert result["success"] is True
        assert "content" in result["output"]

    def test_monthly_report(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        analyst.call_llm = MagicMock(return_value="# 月次レポート\n## 概要\n...")
        result = analyst.execute(
            {
                "task_type": "monthly_report",
                "context": {
                    "month_data": {"leads": 50, "conversions": 5},
                    "previous_month_data": {"leads": 40, "conversions": 4},
                },
            }
        )
        assert result["success"] is True
        assert "content" in result["output"]

    def test_pattern_extraction(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        analyst.call_llm = MagicMock(
            return_value='{"patterns": [{"pattern": "朝投稿が反応良い"}], "recommendations": ["7時投稿を継続"]}'
        )
        result = analyst.execute(
            {
                "task_type": "pattern_extraction",
                "context": {
                    "content_data": [{"title": "記事1", "engagement": 100}],
                },
            }
        )
        assert result["success"] is True

    def test_unknown_task_type(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        result = analyst.execute({"task_type": "unknown", "context": {}})
        assert "error" in result


class TestOrchestrator:
    """Tests for Orchestrator."""

    def test_init(self) -> None:
        from src.orchestrator import Orchestrator

        orch = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        assert "lead_strategist" in orch.agents
        assert len(orch.agents) == 8

    def test_delegate_unknown_agent(self) -> None:
        from src.orchestrator import Orchestrator

        orch = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        result = orch.delegate("nonexistent", {})
        assert "error" in result

    def test_extract_content_text_from_dict(self) -> None:
        from src.orchestrator import Orchestrator

        orch = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        assert orch._extract_content_text({"content": "本文"}) == "本文"
        assert orch._extract_content_text({"body": "メール"}) == "メール"
        assert orch._extract_content_text({"script": "台本"}) == "台本"


class TestScheduler:
    """Tests for Scheduler."""

    def test_add_task(self) -> None:
        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("test", 7, 0, lambda: "result")
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0].name == "test"

    def test_list_tasks(self) -> None:
        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("morning", 7, 0, lambda: "ok", description="朝報")
        tasks = scheduler.list_tasks()
        assert tasks[0]["schedule"] == "07:00"
        assert tasks[0]["description"] == "朝報"

    def test_weekday_only_task(self) -> None:
        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("weekday_task", 9, 0, lambda: "ok", weekday_only=True)
        task = scheduler.tasks[0]
        assert task.weekday_only is True

    def test_build_default_scheduler(self) -> None:
        from src.orchestrator import Orchestrator
        from src.scheduler import build_default_scheduler

        orchestrator = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        scheduler = build_default_scheduler(orchestrator)
        task_names = [t.name for t in scheduler.tasks]
        assert "morning_brief" in task_names

    def test_get_due_tasks(self) -> None:
        from datetime import datetime

        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("test", 7, 0, lambda: "result")
        due = scheduler.get_due_tasks(datetime(2026, 5, 23, 8, 0, 0))
        assert len(due) == 1

    def test_next_run(self) -> None:
        from datetime import datetime

        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("test", 7, 0, lambda: "result")
        next_time = scheduler.next_run("test", datetime(2026, 5, 23, 6, 0, 0))
        assert next_time.hour == 7

    def test_failed_task_not_retried_same_day(self) -> None:
        from datetime import datetime, timedelta

        from src.scheduler import Scheduler

        def failing() -> None:
            raise RuntimeError("API down")

        scheduler = Scheduler()
        scheduler.add_task("flaky", 7, 0, failing)
        now = datetime(2026, 5, 23, 7, 0, 0)

        results = scheduler.run_due_tasks(now)
        assert results[0]["success"] is False

        # 1分後の再ティックでは再実行されない（APIを叩き続けない）
        assert scheduler.get_due_tasks(now + timedelta(minutes=1)) == []
        # 翌日は再び実行対象になる
        assert len(scheduler.get_due_tasks(now + timedelta(days=1))) == 1


class TestSkillLoader:
    """Tests for SkillLoader."""

    def test_available_skills(self) -> None:
        from src.skills import SkillLoader

        skills = SkillLoader.available()
        assert "garai-tone" in skills
        assert "dream-writing" in skills

    def test_load_existing_skill(self) -> None:
        from src.skills import SkillLoader

        content = SkillLoader.load("garai-tone")
        assert len(content) > 0

    def test_load_nonexistent_skill(self) -> None:
        from src.skills import SkillLoader

        content = SkillLoader.load("nonexistent-skill-xyz")
        assert "not found" in content.lower() or "Skill" in content


class TestFormatBrandDna:
    """Tests for format_brand_dna."""

    def test_format(self) -> None:
        from src.skills import format_brand_dna

        text = format_brand_dna(BRAND_DNA)
        assert "TestBrand" in text
        assert "プロフェッショナル" in text
        assert "絶対" in text
