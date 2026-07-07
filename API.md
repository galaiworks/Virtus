# API Reference

Virtus エージェント API リファレンスです。**実装 (`src/`) と同期しています。**

---

## 共通インターフェース

### BaseAgent

すべてのエージェントの基底クラス。API エラーは SDK レベルで自動リトライ（3回）＋タイムアウト（120秒）。

```python
from src.agents.base import BaseAgent

class BaseAgent(ABC):
    MAX_API_RETRIES = 3
    API_TIMEOUT_SECONDS = 120.0

    def __init__(
        self,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None: ...

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """タスクを実行し結果を返す"""
        ...

    def call_llm(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str: ...

    def get_brand_colors(self) -> list[str]: ...
    def get_brand_fonts(self) -> dict[str, str]: ...
```

**共通の戻り値形式**（各エージェントの `execute`）:

```python
{"task_type": "...", "success": True, "output": {...}}
# または
{"error": "Unknown task type: ..."}
```

---

## Lead Strategist

戦略統括。モデル: `claude-opus-4-7`

| task_type | 説明 |
|-----------|------|
| `morning_brief` | 朝報を生成 |
| `weekly_review` | 週次レビュー |
| `monthly_review` | 月次レビュー |
| `delegate_task` | タスクを他エージェントに分配 |

```python
from src.agents import LeadStrategist

ls = LeadStrategist(api_key="sk-...", brand_dna=brand_dna)

result = ls.execute({
    "task_type": "morning_brief",
    "context": {
        "current_date": "2026-05-24",
        "yesterday_data": {...},
        "active_leads": [...],
        "active_deals": [...],
        "kpi_status": {...},
    },
})
# => {"task_type": "morning_brief", "success": True,
#     "output": {"date": "2026-05-24", "content": "おはようございます..."}}
```

`delegate_task` は `context={"goal": "...", "available_agents": [...]}` を受け取り、
`output` に `delegations` / `execution_order` / `rationale` を返す（JSON解析失敗時は `raw_response`）。

---

## Researcher

調査。モデル: `claude-sonnet-4-6`

| task_type | 説明 | 主な context |
|-----------|------|--------------|
| `trend_research` | トレンド抽出 | `target_keywords`, `source_materials`, `period` |
| `competitor_watch` | 競合監視 | `competitors`, `source_materials` |
| `keyword_research` | SEOキーワード提案 | `seed_keywords`, `existing_topics` |
| `summarize_sources` | ソース要約 | `sources`, `focus` |

```python
result = researcher.execute({
    "task_type": "trend_research",
    "context": {
        "target_keywords": ["AI", "自動化"],
        "source_materials": [{"url": "https://...", "content": "..."}],
        "period": "直近7日",
    },
})
# => output: {"content": "【業界トレンド】...", "period": "直近7日"}
```

**原則**: ソース資料にない情報は捏造しない。各トレンドにソースURL必須。

---

## Drafter

執筆。モデル: `claude-sonnet-4-6`
デフォルトスキル: `garai-tone`, `dream-writing`, `impact-v2-0r`

| task_type | 説明 |
|-----------|------|
| `note_article` | note 記事 |
| `x_post` | X 投稿（スレッド対応） |
| `outreach_email` | 営業メール |
| `proposal` | 提案書 |
| `instagram_carousel` | カルーセル原稿 |
| `youtube_script` | YouTube 台本 |
| （その他） | `write_generic` にフォールバック（`success: False`） |

```python
result = drafter.execute({
    "task_type": "note_article",
    "context": {
        "topic": "AIエージェントの可能性",
        "target_audience": "ひとり社長",
        "length_target": 2500,
    },
})
```

### refine(content, feedback, content_type="generic")

Guardian のフィードバックを反映した修正版テキストを返す。95点ループから呼ばれる。

```python
refined: str = drafter.refine(
    content="元のコンテンツ...",
    feedback="第3段落の語尾を変更してください",
    content_type="note_article",
)
```

---

## Designer

ビジュアル生成。モデル: `claude-sonnet-4-6`
HyperFrames（HTML→MP4）+ Video-Use（AI編集）統合。

| task_type | 説明 |
|-----------|------|
| `video` | HyperFrames で動画生成 |
| `edit_footage` | Video-Use で素材編集 |
| `overlay` | オーバーレイ生成 |
| `full_production` | 素材→編集→オーバーレイの一括制作 |

```python
designer = Designer(api_key="sk-...", brand_dna=brand_dna, output_dir=Path("output"))

result = designer.execute({
    "task_type": "video",
    "context": {
        "platform": "youtube",   # サイズ自動設定
        "title": "AIエージェントの未来",
        "content_text": "...",
        "duration": 15.0,
    },
})
```

---

## Distributor

配信。モデル: `claude-haiku-4-5`

| task_type | 説明 |
|-----------|------|
| `schedule_post` | スケジュール配信（`approval_status: "approved"` 必須） |
| `immediate_post` | 即時配信 |
| `send_email` | メール送信（特定電子メール法準拠を自動付与） |
| `calculate_optimal_time` | 配信タイミング最適化 |

```python
result = distributor.execute({
    "task_type": "schedule_post",
    "context": {
        "approval_status": "approved",  # 未承認は error
        "platform": "note",
        "content": {"title": "...", "body": "..."},
        "scheduled_time": "2026-05-24T09:00:00+09:00",
    },
})
```

**ガード**: 未承認コンテンツは配信拒否。X 280文字制限、Instagram ハッシュタグ30個制限、スパム表現を自動チェック。

---

## Connector

DM・関係構築。モデル: `claude-sonnet-4-6`

| task_type | 説明 |
|-----------|------|
| `draft_dm_reply` | DM 返信ドラフト |
| `draft_comment_reply` | コメント返信ドラフト |
| `check_escalation` | エスカレーション判定のみ |
| `plan_follow_up` | フォローアップ計画 |

```python
result = connector.execute({
    "task_type": "draft_dm_reply",
    "context": {
        "incoming_message": {"text": "サービスについて質問があります"},
        "sender_profile": {"username": "prospect_001"},
        "interaction_history": [],
        "platform": "x",
    },
})
# 通常: output = {"reply_draft": {"message": "..."}, "flag_for_attention": false}
# 危険ワード検出時: output = {"escalation_required": True, "escalation_level": 4, ...}
```

**エスカレーションキーワード**: Level 4（弁護士・訴訟・詐欺等）/ Level 3（クレーム・返金等）/ Level 2（検討します等）

`plan_follow_up` の `sequence_type`: `no_reply_first_outreach` / `post_meeting` / `post_purchase`

---

## Analyst

分析。モデル: `claude-sonnet-4-6`

| task_type | 説明 |
|-----------|------|
| `weekly_summary` | 週次サマリー |
| `monthly_report` | 月次レポート |
| `pattern_extraction` | 勝ちパターン抽出 |
| `kpi_dashboard` | KPI ダッシュボード（LLM 不使用・ルールベース） |

```python
result = analyst.execute({
    "task_type": "kpi_dashboard",
    "context": {
        "current_metrics": {"content_volume": 35, "lead_acquisition": 22},
        "tier": 1,
    },
})
# => output["kpis"]["content_volume"]["status"]  # "達成"/"順調"/"要注意"/"未達"
```

---

## Guardian

品質保証。モデル: `claude-opus-4-7`、閾値 95 点。

| task_type | 説明 |
|-----------|------|
| `evaluate` | 単発評価 |
| `evaluate_with_loop` | 95 点ループ |

### evaluate(content, content_type="default") → Evaluation

ルールベースチェック（特定電子メール法・過剰約束）＋ LLM 評価。
重大違反（CRITICAL）は即 `total_score=0` / `verdict="CRITICAL_VIOLATION"`。

```python
evaluation = guardian.evaluate("コンテンツ...", "note_article")
evaluation.total_score   # int（LLMが文字列を返しても強制変換）
evaluation.verdict       # "APPROVED" | "REJECTED" | "CRITICAL_VIOLATION"
evaluation.force_reject  # CRITICAL 違反があれば True
```

### evaluate_with_loop(content, content_type, agent_name, revise_fn=None, max_retries=None)

```python
result = guardian.evaluate_with_loop(
    content="...",
    content_type="note_article",
    agent_name="Drafter",
    revise_fn=lambda content, feedback: drafter.refine(content, feedback),
    max_retries=3,  # None なら Guardian.MAX_RETRIES (3)
)
# result["status"]: "approved" | "needs_revision" | "escalated"
# result["evaluation"]: dict（total_score, verdict, axis_scores, violations, feedback）
# result["retry_count"]: int
# escalated 時: result["reason"] = "critical_violation" | "max_retries_exceeded"
```

**注意**: `result["evaluation"]` は **dict** です（Evaluation オブジェクトではない）。

コンテンツタイプ別の評価配点は `Guardian.EVALUATION_WEIGHTS`
（`outreach_email` は法令遵守 35 点、`x_post` はブランドDNA 35 点など）。

---

## Orchestrator

```python
from src.orchestrator import Orchestrator
from src.brain import BrainLayer

orchestrator = Orchestrator(
    api_key="sk-...",
    brand_dna=brand_dna,
    output_dir=Path("output"),          # 省略可
    brain=BrainLayer(),                 # 省略可: 指定すると監査ログを自動記録
    customer_id="founding_001",         # brain とセットで指定
)
```

### write_and_review(content_type, context, max_retries=3)

Drafter 執筆 → Guardian 95 点ループ。`brain` 指定時は `logs/evaluations.jsonl` に自動記録。

```python
result = orchestrator.write_and_review(
    content_type="note_article",
    context={"topic": "AIエージェントの未来", "target_audience": "ひとり社長"},
)
# {"status": "approved", "content": "...", "draft_output": {...},
#  "evaluation": {...dict...}, "retry_count": 0}
# 失敗時: {"status": "draft_failed", "error": "..."}
```

### morning_brief(context)

Lead Strategist に委譲。

### full_content_pipeline(topic, target_audience, platforms)

```python
results = orchestrator.full_content_pipeline(
    topic="AIエージェント入門",
    target_audience="ひとり社長",
    platforms=["note_article", "x_post"],
)
# => {"platforms": {"note_article": {...}, "x_post": {...}}}
```

### handle_incoming_message(message_context)

Connector → Guardian。エスカレーション時は `logs/escalations.jsonl` に記録（brain 指定時）。

```python
result = orchestrator.handle_incoming_message({
    "incoming_message": {"text": "質問があります"},
    "sender_profile": {},
    "platform": "x",
})
# status: "ready_for_approval" | "needs_revision" | "escalated" | "no_reply_generated"
```

### delegate(agent_name, task)

エージェント名（`lead_strategist` / `researcher` / `drafter` / `designer` /
`distributor` / `connector` / `analyst` / `guardian`）で直接タスク委譲。

---

## Scheduler

```python
from src.scheduler import Scheduler, build_default_scheduler

scheduler = Scheduler()
scheduler.add_task(
    name="morning_brief",
    hour=7,
    minute=0,
    callback=lambda: orchestrator.morning_brief({...}),
    weekday_only=False,
    description="毎朝7時の朝報",
)

# 実行はポーリング型（cron等から毎分呼ぶ想定）
results = scheduler.run_due_tasks()   # 期限が来たタスクを実行
scheduler.get_due_tasks()             # 実行対象の確認のみ
scheduler.next_run("morning_brief")   # 次回実行時刻
scheduler.list_tasks()                # 登録タスク一覧

# デフォルト構成（朝報 + 週次レビュー）
scheduler = build_default_scheduler(orchestrator)
```

**挙動**: 各タスクは 1 日 1 回。失敗しても `last_run` を更新し、翌日まで再実行しない
（失敗は `run_due_tasks` の戻り値 `{"success": False, "error": ...}` で通知）。

---

## Brain Layer

顧客データの永続化（BYOK 原則: ローカルのみ保存）。

```python
from src.brain import BrainLayer, BrandDNA, ContentRecord, generate_content_id

brain = BrainLayer(brain_root=Path("brain"))  # 省略時は ./brain
```

| メソッド | 説明 |
|----------|------|
| `init_customer(customer_id)` | ディレクトリ初期化 |
| `customer_exists(customer_id)` | 存在確認 |
| `save_brand_dna(customer_id, brand_dna)` | BrandDNA / dict を YAML 保存 |
| `load_brand_dna(customer_id)` | → `BrandDNA \| None` |
| `load_brand_dna_dict(customer_id)` | → `dict`（エージェントに渡す用） |
| `save_content(customer_id, record)` | ContentRecord を JSON 保存 |
| `load_content(customer_id, content_id)` | → `ContentRecord \| None` |
| `list_content(customer_id, content_type=None, limit=None)` | 新しい順 |
| `save_learning_data(customer_id, data_type, data)` | 学習データ保存 |
| `load_learning_data(customer_id, data_type)` | → `dict \| None` |
| `append_log(customer_id, log_type, entry)` | JSONL 監査ログ追記（timestamp 自動付与） |
| `read_logs(customer_id, log_type, limit=100)` | 新しい順 |
| `delete_customer(customer_id)` | 完全削除（契約終了時） |
| `export_customer_data(customer_id, export_path)` | データエクスポート |

### データ構造

```python
@dataclass
class BrandDNA:
    identity: dict[str, Any]
    voice: dict[str, Any]
    content_strategy: dict[str, Any]
    forbidden: dict[str, Any]
    reference: dict[str, Any]
    # to_dict() / from_dict() あり

@dataclass
class ContentRecord:
    content_id: str
    content_type: str
    title: str
    content: str
    platform: str
    created_at: str
    published_at: str | None = None
    guardian_score: int | None = None
    metrics: dict[str, Any] = ...
```

`generate_content_id()` はユニークID、`build_default_brand_dna()` はテンプレを返す。

---

## Onboarding

30 問ヒアリング → BrandDNA 生成。

```python
from src.onboarding import OnboardingFlow, HEARING_QUESTIONS, analyze_past_content

flow = OnboardingFlow(api_key="sk-...")

flow.start_session("new_customer")                # → HearingSession
q = flow.get_current_question("new_customer")     # → HearingQuestion | None（dataclass）
print(q.id, q.category, q.question)               # 属性アクセス（dict ではない）

flow.submit_answer("new_customer", q.id, "回答")
flow.get_progress("new_customer")
# => {"current": 1, "total": 30, "completed": False, "percentage": 3}

brand_dna = flow.generate_brand_dna("new_customer")  # → BrandDNA | None

# 過去コンテンツの voice 分析（モジュール関数）
voice = analyze_past_content(api_key="sk-...", content_samples=["記事本文...", ...])
```

---

## Skills

```python
from src.skills import SkillLoader, format_brand_dna

SkillLoader.available()          # → ["garai-tone", "dream-writing", ...]
SkillLoader.load("garai-tone")   # → SKILL.md の内容
SkillLoader.load_many(["garai-tone", "dream-writing"])

format_brand_dna(brand_dna_dict)  # → プロンプト注入用テキスト
```

---

## エラーハンドリング

```python
result = orchestrator.write_and_review(content_type, context)

match result["status"]:
    case "approved":
        ...  # 人間承認キューへ
    case "needs_revision":
        ...  # revise_fn なしで 95 点未満
    case "escalated":
        # result["reason"]: "critical_violation" | "max_retries_exceeded"
        ...  # 人間にエスカレーション
    case "draft_failed":
        ...  # Drafter 自体が失敗
```

---

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Anthropic API キー（BYOK: 顧客が自己管理） |

## モデル割り当て

| モデル ID | エージェント |
|-----------|--------------|
| `claude-opus-4-7` | Lead Strategist, Guardian |
| `claude-sonnet-4-6` | Researcher, Drafter, Designer, Connector, Analyst |
| `claude-haiku-4-5` | Distributor |
