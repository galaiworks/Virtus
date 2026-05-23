# Contributing to Virtus

Virtus プロジェクトへの貢献ガイドです。

---

## 開発環境のセットアップ

### 必須要件

- Python 3.11 以上
- Git

### セットアップ手順

```bash
git clone <repo-url>
cd virtus
pip install -e ".[dev]"
```

### 環境変数

```bash
cp .env.example .env
# ANTHROPIC_API_KEY を設定
```

---

## 開発フロー

### 1. ブランチ作成

```bash
git checkout -b feat/your-feature-name
```

### 2. 開発

コードを書いて、テストを追加。

### 3. テスト実行

```bash
pytest tests/ -v
```

### 4. リント・フォーマット

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### 5. 型チェック

```bash
mypy src/ --ignore-missing-imports
```

### 6. コミット

```bash
git add .
git commit -m "feat(agent): 新機能追加"
```

### 7. プルリクエスト

GitHub 上で PR を作成。

---

## コーディング規約

### Python スタイル

- **Python 3.11 以上** を使用
- **型ヒント必須**
- **docstring** を各関数に記述
- **ruff** でリント・フォーマット

### ファイル命名

```
src/agents/lead_strategist.py   # スネークケース
.claude/agents/lead-strategist.md  # ハイフン区切り
tests/test_lead_strategist.py   # test_ プレフィックス
```

### コミットメッセージ

```
feat: 新機能追加
fix: バグ修正
refactor: リファクタリング
docs: ドキュメント更新
test: テスト追加・修正
chore: その他
```

例:

```
feat(drafter): X投稿生成機能を追加
fix(guardian): 95点ループの境界条件を修正
test(e2e): 1日のワークフローテストを追加
```

---

## ディレクトリ構造

```
virtus/
├── src/                    # 実装コード
│   ├── agents/             # 8体エージェント
│   ├── video/              # 動画生成
│   ├── orchestrator.py     # オーケストレーター
│   ├── scheduler.py        # スケジューラー
│   ├── brain.py            # データ永続化
│   ├── onboarding.py       # オンボーディング
│   └── skills.py           # スキルローダー
├── .claude/                # Claude Code 設定
│   ├── agents/             # エージェント定義
│   ├── skills/             # スキル定義
│   └── rules/              # ルール定義
├── tests/                  # テストコード
├── scripts/                # 運用スクリプト
├── brain/                  # 顧客データ (.gitignore)
└── logs/                   # ログ (.gitignore)
```

---

## エージェント実装ガイド

### 基底クラス

すべてのエージェントは `BaseAgent` を継承:

```python
from src.agents.base import BaseAgent

class NewAgent(BaseAgent):
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
        """メイン処理"""
        task_type = task.get("task_type")
        context = task.get("context", {})
        # 実装
        return {"status": "success", ...}
```

### モデル選択

| 用途 | モデル |
|------|--------|
| 戦略・品質判断 | claude-opus-4-7 |
| 一般タスク | claude-sonnet-4-6 |
| 軽量タスク | claude-haiku-4-5 |

---

## テスト

### テストの種類

1. **ユニットテスト** - 単一関数・メソッド
2. **統合テスト** - エージェント間連携
3. **E2E テスト** - ワークフロー全体

### テスト実行

```bash
# 全テスト
pytest tests/ -v

# カバレッジ付き
pytest tests/ --cov=src --cov-report=term-missing

# 特定ファイル
pytest tests/test_drafter.py -v

# 特定テスト
pytest tests/test_integration.py::TestDrafterGuardianLoop -v
```

### モック

API 呼び出しは `unittest.mock.patch` でモック:

```python
from unittest.mock import patch

def test_example():
    with patch.object(Drafter, "call_llm", return_value="mocked"):
        result = drafter.execute(task)
```

---

## 重要な原則

### 1. 95 点品質ループ

すべての対外出力は Guardian が 95 点以上でなければ承認されない。

### 2. BYOK

顧客の API キーは galaiworks サーバーに永続保存しない。

### 3. 法令遵守

- ブラウザ自動化禁止
- 無断スクレイピング禁止
- スパム送信禁止
- すべて公式 API 経由

### 4. ブランド DNA

すべての出力は顧客のブランド DNA に準拠する。

---

## よくある質問

### Q: 新しいエージェントを追加したい

1. `src/agents/new_agent.py` を作成
2. `BaseAgent` を継承
3. `.claude/agents/new-agent.md` でプロンプト定義
4. `tests/test_agents/test_new_agent.py` でテスト作成
5. `src/agents/__init__.py` にエクスポート追加

### Q: 新しいスキルを追加したい

1. `.claude/skills/new-skill/SKILL.md` を作成
2. `src/skills.py` の `load_skill` で読み込み
3. テスト追加

### Q: テストが失敗する

```bash
# 詳細ログを見る
pytest tests/failing_test.py -v --tb=long

# 特定のテストだけ実行
pytest tests/failing_test.py::test_name -v
```

---

## リリースプロセス

### Phase 1 (Founding Members)

- Claude Code 環境での動作
- 手動デプロイ

### Phase 2 以降

- Web UI
- CI/CD パイプライン
- 自動デプロイ

---

## 連絡先

- **開発者**: galaiworks
- **Issues**: GitHub Issues で報告

---

## ライセンス

Proprietary. All rights reserved.
