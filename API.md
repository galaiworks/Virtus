# API Reference

Virtus エージェント API リファレンスです。

---

## 共通インターフェース

### BaseAgent

すべてのエージェントの基底クラス。

```python
from src.agents.base import BaseAgent

class BaseAgent(ABC):
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
    ) -> str:
        """LLM を呼び出す"""
        ...
```

---

## Lead Strategist

戦略統括・オーケストレーター。

```python
from src.agents import LeadStrategist

strategist = LeadStrategist(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `morning_brief` | 朝報を生成 |
| `weekly_review` | 週次レビューを生成 |
| `monthly_review` | 月次レビューを生成 |
| `delegate` | タスクを他エージェントに委譲 |

#### morning_brief

```python
result = strategist.execute({
    "task_type": "morning_brief",
    "context": {},
})
# => {"status": "success", "brief": {...}}
```

#### delegate

```python
result = strategist.execute({
    "task_type": "delegate",
    "context": {
        "target_agent": "Researcher",
        "task": {...},
    },
})
```

---

## Researcher

探索・調査・能動営業。

```python
from src.agents import Researcher

researcher = Researcher(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `trend_research` | トレンド調査 |
| `competitor_watch` | 競合監視 |
| `seo_keywords` | SEO キーワード調査 |

```python
result = researcher.execute({
    "task_type": "trend_research",
    "context": {
        "topic": "AI エージェント",
        "depth": "detailed",
    },
})
# => {"status": "success", "findings": [...]}
```

---

## Drafter

全コンテンツ執筆。

```python
from src.agents import Drafter

drafter = Drafter(
    api_key="sk-...",
    brand_dna=brand_dna,
    skills=["garai-tone", "dream-writing"],
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `note_article` | note 記事執筆 |
| `x_post` | X 投稿生成 |
| `email` | メール文面 |
| `proposal` | 提案書 |
| `carousel` | カルーセル原稿 |
| `youtube_script` | YouTube 台本 |

```python
result = drafter.execute({
    "task_type": "note_article",
    "context": {
        "topic": "AI エージェントの可能性",
        "target_length": 2000,
        "style": "garai-tone",
    },
})
# => {"status": "success", "content": "...", "title": "..."}
```

### refine(content, feedback)

Guardian からのフィードバックに基づいてコンテンツを改善。

```python
refined = drafter.refine(
    content="元のコンテンツ...",
    feedback="第3段落の語尾を変更してください",
)
```

---

## Designer

ビジュアル生成。

```python
from src.agents import Designer

designer = Designer(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `thumbnail` | サムネイル生成 |
| `short_video` | ショート動画生成 |
| `carousel_images` | カルーセル画像 |

```python
result = designer.execute({
    "task_type": "thumbnail",
    "context": {
        "title": "AI エージェントの未来",
        "style": "modern",
    },
})
# => {"status": "success", "image_path": "..."}
```

---

## Distributor

配信処理。

```python
from src.agents import Distributor

distributor = Distributor(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `schedule` | 配信スケジュール設定 |
| `distribute` | 即時配信 |
| `optimize_timing` | 配信タイミング最適化 |

```python
result = distributor.execute({
    "task_type": "schedule",
    "context": {
        "content": "...",
        "platform": "note",
        "scheduled_time": "2026-05-24T09:00:00+09:00",
    },
})
```

---

## Connector

DM・関係構築。

```python
from src.agents import Connector

connector = Connector(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `dm_reply` | DM 返信 |
| `comment_reply` | コメント返信 |
| `followup` | フォローアップ計画 |

```python
result = connector.execute({
    "task_type": "dm_reply",
    "context": {
        "incoming_message": "サービスについて質問があります",
        "sender": "prospect_001",
    },
})
# => {"status": "success", "reply": "...", "escalate": False}
```

---

## Analyst

分析・学習。

```python
from src.agents import Analyst

analyst = Analyst(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `weekly_summary` | 週次サマリー |
| `monthly_report` | 月次レポート |
| `pattern_analysis` | パターン抽出 |

```python
result = analyst.execute({
    "task_type": "monthly_report",
    "context": {
        "period": "2026-05",
    },
})
# => {"status": "success", "report": {...}}
```

---

## Guardian

品質保証・95 点ループ。

```python
from src.agents import Guardian

guardian = Guardian(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### execute(task)

| task_type | 説明 |
|-----------|------|
| `evaluate` | コンテンツ評価 |
| `evaluate_with_loop` | 95 点ループ評価 |

### evaluate(content, content_type)

```python
from src.agents.guardian import Evaluation

evaluation: Evaluation = guardian.evaluate(
    content="評価対象のコンテンツ...",
    content_type="note_article",
)
# => Evaluation(total_score=92, verdict="REJECTED", ...)
```

### evaluate_with_loop(content, content_type, agent_name, revise_fn)

```python
result = guardian.evaluate_with_loop(
    content="コンテンツ...",
    content_type="note_article",
    agent_name="Drafter",
    revise_fn=drafter.refine,
)
# => {"status": "approved", "content": "...", "evaluation": {...}}
# or {"status": "escalated", "reason": "max_retries_exceeded", ...}
```

---

## Orchestrator

エージェント間連携を統括。

```python
from src.orchestrator import Orchestrator

orchestrator = Orchestrator(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### write_and_review(topic, content_type)

Drafter + Guardian の 95 点ループ。

```python
result = orchestrator.write_and_review(
    topic="AI エージェントの未来",
    content_type="note_article",
)
# => {"status": "approved", "content": "...", ...}
```

### handle_incoming_message(message, sender, platform)

Connector + Guardian によるメッセージ処理。

```python
result = orchestrator.handle_incoming_message(
    message="質問があります",
    sender="user_001",
    platform="twitter",
)
# => {"status": "replied", "reply": "...", ...}
```

### full_content_pipeline(topic, platforms)

マルチプラットフォームコンテンツ生成。

```python
result = orchestrator.full_content_pipeline(
    topic="AI エージェント入門",
    platforms=["note", "x", "linkedin"],
)
# => {"note": {...}, "x": {...}, "linkedin": {...}}
```

---

## Scheduler

定期タスクのスケジューリング。

```python
from src.scheduler import Scheduler, ScheduledTask, build_default_scheduler

scheduler = build_default_scheduler(
    api_key="sk-...",
    brand_dna=brand_dna,
)
```

### add_task(task)

```python
from src.scheduler import ScheduledTask

task = ScheduledTask(
    name="morning_brief",
    hour=7,
    minute=0,
    task_type="morning_brief",
    weekdays_only=True,
)
scheduler.add_task(task)
```

### run()

```python
scheduler.run()  # ブロッキング実行
```

---

## Brain Layer

顧客データの永続化。

```python
from src.brain import BrainLayer, BrandDNA, ContentRecord

brain = BrainLayer(base_path="brain")
```

### init_customer(customer_id)

```python
brain.init_customer("customer_001")
```

### save_brand_dna / load_brand_dna

```python
brand_dna = BrandDNA(
    name="galaiworks",
    tagline="世界基準のAI",
    identity={...},
    voice={...},
    forbidden={...},
)
brain.save_brand_dna("customer_001", brand_dna)

loaded = brain.load_brand_dna("customer_001")
```

### save_content / list_content

```python
from src.brain import ContentRecord, generate_content_id

record = ContentRecord(
    content_id=generate_content_id(),
    content_type="note_article",
    title="記事タイトル",
    content="本文...",
    status="approved",
    score=96,
    created_at="2026-05-23T10:00:00+09:00",
)
brain.save_content("customer_001", record)

contents = brain.list_content("customer_001", limit=10)
```

### append_log / read_logs

```python
brain.append_log("customer_001", {
    "event": "content_approved",
    "content_id": "abc123",
    "score": 96,
})

logs = brain.read_logs("customer_001", limit=100)
```

---

## Onboarding

顧客オンボーディングフロー。

```python
from src.onboarding import OnboardingFlow

onboarding = OnboardingFlow(api_key="sk-...")
```

### start_session(customer_id)

```python
session = onboarding.start_session("new_customer")
# 30 問のヒアリング開始
```

### get_current_question(customer_id)

```python
question = onboarding.get_current_question("new_customer")
# => {"id": "Q01", "category": "Identity", "question": "..."}
```

### submit_answer(customer_id, question_id, answer)

```python
onboarding.submit_answer("new_customer", "Q01", "galaiworks")
```

### generate_brand_dna(customer_id)

```python
brand_dna = onboarding.generate_brand_dna("new_customer")
# => BrandDNA(...)
```

### analyze_past_content(urls)

```python
voice_analysis = onboarding.analyze_past_content([
    "https://note.com/...",
    "https://example.com/...",
])
```

---

## Skills

スキルの読み込み・フォーマット。

```python
from src.skills import load_skill, format_brand_dna, load_all_skills

skill = load_skill("garai-tone")
# => "Garai Tone スキルの内容..."

all_skills = load_all_skills(["garai-tone", "dream-writing"])

formatted = format_brand_dna(brand_dna)
# => "name: galaiworks\ntagline: ..."
```

---

## データ構造

### BrandDNA

```python
@dataclass
class BrandDNA:
    name: str
    tagline: str
    identity: dict[str, Any]
    voice: dict[str, Any]
    forbidden: dict[str, Any]
    content_strategy: dict[str, Any] = field(default_factory=dict)
    reference: dict[str, Any] = field(default_factory=dict)
```

### ContentRecord

```python
@dataclass
class ContentRecord:
    content_id: str
    content_type: str
    title: str
    content: str
    status: str
    score: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Evaluation

```python
@dataclass
class Evaluation:
    total_score: int
    verdict: str  # "APPROVED" | "REJECTED" | "CRITICAL_VIOLATION"
    axis_scores: dict[str, dict[str, Any]]
    violations: list[Violation]
    feedback: str
    raw_response: str
```

### Violation

```python
@dataclass
class Violation:
    severity: str  # "CRITICAL" | "MAJOR" | "MINOR"
    category: str
    description: str
    location: str = ""
    fix_suggestion: str = ""
```

---

## エラーハンドリング

### エスカレーション

```python
result = orchestrator.write_and_review(topic, content_type)

if result["status"] == "escalated":
    reason = result["reason"]
    # "critical_violation" or "max_retries_exceeded"
    # 人間にエスカレーション
```

### Guardian 評価失敗

```python
evaluation = guardian.evaluate(content, content_type)

if evaluation.force_reject:
    # 重大違反、即時停止
    ...

if evaluation.total_score < 95:
    # 改善が必要
    ...
```

---

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Anthropic API キー |

---

## モデル一覧

| モデル ID | 用途 |
|-----------|------|
| `claude-opus-4-7` | 戦略・品質判断 |
| `claude-sonnet-4-6` | 一般タスク |
| `claude-haiku-4-5` | 軽量タスク |
