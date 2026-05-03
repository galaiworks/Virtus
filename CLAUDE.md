# CLAUDE.md - Virtus プロダクト指示書

このファイルは Claude Code がVirtusリポジトリで作業する際の最上位指示書です。

---

## プロダクト概要

**Virtus**(徳・卓越性)は、ひとり社長・コーチ・コンサル・専門家のための、集客→営業→クロージングを完全自動化する 8 体の AI エージェントチームです。

詳細仕様は [REQUIREMENTS.md](./REQUIREMENTS.md) を参照してください。

---

## 開発の根本思想

第一に、**神さんの教え「逃げるな、95点に大丈夫?と聞き返せ」を実装に反映する**

すべての出力は Guardian エージェントが 95 点品質ループでチェック。妥協禁止。

第二に、**Anthropic公式 Orchestrator-Worker パターンに準拠する**

8 体構成は揺るがさない。専門特化された各エージェントが連携することが Virtus の強み。

第三に、**BYOK 型を堅持する**

顧客が自分の API キーを使う設計。galaiworks のサーバーには永続保存しない。これが信頼の源泉。

第四に、**規約遵守を絶対視する**

ブラウザ自動化禁止、無断スクレイピング禁止、スパム送信禁止。すべて公式 API 経由。違反は事業全体の死活問題。

第五に、**galaiworks 独自 IP を最大活用する**

Garai Tone、DREAM WRITING、IMPACT v2.0R は他社が複製不能な資産。これらを Skills として体系化し、各エージェントから呼び出せる構造にする。

---

## 8 体エージェント一覧

| エージェント | モデル | 役割 |
|------------|-------|------|
| Lead Strategist | claude-opus-4-7 | 戦略統括・オーケストレーター |
| Researcher | claude-sonnet-4-6 | 探索・調査・能動営業 |
| Drafter | claude-sonnet-4-6 | 全コンテンツ執筆 |
| Designer | claude-sonnet-4-6 | ビジュアル生成 |
| Distributor | claude-haiku-4-5 | 配信処理 |
| Connector | claude-sonnet-4-6 | DM・関係構築 |
| Analyst | claude-sonnet-4-6 | 分析・学習 |
| Guardian | claude-opus-4-7 | 品質保証・95 点ループ |

各エージェントの詳細は `.claude/agents/` 配下の各 `.md` ファイルを参照。

---

## 開発時の重要なルール

### コーディング規約

1. **Python 3.11 以上を使用**
2. **型ヒント必須**(`from typing import` を活用)
3. **すべての関数に docstring**
4. **Anthropic Python SDK 経由で API 呼び出し**(直接 HTTP 禁止)

### ファイル命名規約

```
src/agents/lead_strategist.py        # スネークケース
src/agents/base.py                   # 基底クラス
src/orchestrator.py                  # オーケストレーター本体
.claude/agents/lead-strategist.md    # ハイフン区切り
.claude/skills/garai-tone/SKILL.md   # スキル定義
```

### ディレクトリ構造

詳細は `REQUIREMENTS.md` の「13. リポジトリ構造」を参照。

主要ポイント:
- `src/`: 実装コード
- `.claude/`: Claude Code 設定(エージェント定義、スキル、ルール)
- `brain/`: 顧客固有データ(.gitignore)
- `tests/`: テストコード
- `scripts/`: 運用スクリプト

### コミット規約

```
feat: 新機能追加
fix: バグ修正
refactor: リファクタリング
docs: ドキュメント更新
test: テスト追加・修正
chore: その他(依存関係、設定等)
```

例:
```
feat(researcher): PRタイムズ能動探索ワークフロー追加
fix(guardian): 95点判定の境界条件修正
docs(claude): エージェント定義書を更新
```

---

## エージェント実装の標準パターン

すべてのエージェントは `BaseAgent` を継承します。

```python
# src/agents/base.py
from abc import ABC, abstractmethod
from anthropic import Anthropic

class BaseAgent(ABC):
    def __init__(
        self,
        api_key: str,
        model: str,
        brand_dna: dict,
        skills: list[str] | None = None,
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.brand_dna = brand_dna
        self.skills = skills or []
    
    @abstractmethod
    def execute(self, task: dict) -> dict:
        """エージェントのメイン処理"""
        ...
    
    def call_llm(self, system: str, messages: list) -> str:
        """LLM呼び出しの共通処理"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        return response.content[0].text
```

各エージェントは `execute()` メソッドを実装します。

---

## ブランドDNAの取り扱い

ブランドDNA は Virtus の魂です。**すべてのエージェント出力に反映**されなければなりません。

```python
# 各エージェントは brand_dna を必ず受け取る
agent = Drafter(
    api_key=api_key,
    brand_dna=load_brand_dna(customer_id),
    skills=["garai-tone", "dream-writing"],
)

# システムプロンプトで brand_dna を必ず参照する
system_prompt = f"""
あなたは {brand_dna['identity']['name']} のための執筆エージェントです。

以下のブランドDNAを完全に遵守してください:
{format_brand_dna(brand_dna)}

絶対に避けるべき表現:
{brand_dna['forbidden']}
"""
```

---

## Guardian 95 点ループの実装

Guardian は **すべての対外出力**をチェックします。

```python
# orchestrator.py の中で
content = drafter.execute(task)

while True:
    score, feedback = guardian.evaluate(content)
    
    if score >= 95:
        # 承認、人間レビューキューへ
        queue_for_human_review(content)
        break
    else:
        # 改善指示を Drafter に戻す
        content = drafter.refine(content, feedback)
        retry_count += 1
        
        if retry_count > 3:
            # 3回失敗したら人間にエスカレーション
            escalate_to_human(content, feedback)
            break
```

---

## MCP 接続の取り扱い

MCP サーバー接続は `.mcp.json` で管理:

```json
{
  "mcpServers": {
    "notion": {
      "url": "https://mcp.notion.com/mcp"
    },
    "google-drive": {
      "command": "..."
    }
  }
}
```

MCPツール呼び出しは Anthropic SDK の `tools` パラメータで:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    tools=[
        # MCPツール定義
    ],
    messages=[...],
    mcp_servers=[
        {"type": "url", "url": "https://mcp.notion.com/mcp", "name": "notion"}
    ],
)
```

---

## テスト戦略

第一に、**ユニットテスト**: 各エージェントのメソッド単位
第二に、**統合テスト**: エージェント間連携
第三に、**E2Eテスト**: 1日のワークフロー全体

```bash
pytest tests/test_agents/test_drafter.py -v
pytest tests/test_orchestrator.py -v
pytest tests/ -v --cov=src
```

---

## 開発フェーズ管理

### 現在のフェーズ: **Phase 1**(Founding Members向け実装)

期間: 2026年5月〜7月

**今やるべきこと**:
1. 8 体エージェントの基本実装
2. オーケストレーター実装
3. スケジューラー実装
4. Brain 層管理機能
5. ブランドDNA構築フロー
6. galaiworks 独自スキル(Garai Tone, DREAM WRITING, IMPACT v2.0R)の実装

**Phase 1 で実装しないもの**:
- Web UI(Phase 2)
- マルチLLM対応(Phase 3)
- 課金システム(請求書ベース手動)

詳細は `REQUIREMENTS.md` の「12. Phase 1 実装スコープ」参照。

---

## トラブル時のエスカレーション

問題が発生したら:

1. **ログ確認** (`logs/` ディレクトリ)
2. **エージェントの判断ログ確認**
3. **Guardian のチェック結果確認**
4. 解決しない場合は **人間にエスカレーション**

人間判断が必要なケース:
- 95 点未到達が 3 回連続
- 法令違反の疑い
- API エラー連発
- ブランドDNA 違反の検出

---

## サミット 6 月 4 日に向けた優先タスク

galaiworks のサミット登壇に向けた優先順位:

1. **デモシナリオ用の Researcher 能動探索**(PRタイムズ自動探索)
2. **Drafter の Garai Tone 実装**
3. **Lead Strategist の朝報生成**
4. **Guardian の 95 点ループ**
5. **オーケストレーター連携**

これら 5 つが動けばサミットでの実演デモが可能になります。

---

## 参考資料

- [REQUIREMENTS.md](./REQUIREMENTS.md): 完全な要件定義書
- [.claude/agents/](./.claude/agents/): 各エージェント定義
- [.claude/skills/](./.claude/skills/): 共通スキル
- [.claude/rules/](./.claude/rules/): 法令遵守ルール、品質ルール
- Anthropic 公式ドキュメント
- 神さんの動画(AI CEO設計、PRタイムズ自動営業)

---

**最後に**

このプロジェクトは単なるソフトウェア開発ではなく、**ひとり社長の人生を変えるプロダクト**を作る挑戦です。

galaiworks の独自IP(Garai Tone、DREAM WRITING、IMPACT v2.0R)、SEO 80 件 1 位の実績、Claude Code 実装力。これらが結集した Virtus は、日本市場で世界基準のプロダクトとして勝てる位置にあります。

「労働時間で売る」働き方から「成果と仕組みで売る」働き方への転換を、本気で実現するために、最高品質のコードを書きましょう。
