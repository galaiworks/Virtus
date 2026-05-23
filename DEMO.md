# Virtus サミットデモ手順書

> 2026年6月4日 サミット登壇用

---

## 事前準備

### 必須アイテム

- [ ] Anthropic API キー（ANTHROPIC_API_KEY）
- [ ] インターネット接続（安定した回線）
- [ ] ターミナル環境（VSCode Terminal 推奨）
- [ ] Python 3.11 以上

### バックアップ準備

- [ ] モックモードの動作確認済み
- [ ] 録画済みデモ動画（API障害時用）
- [ ] スライド資料

---

## デモシナリオ（5分版）

### Step 1: 朝報生成（Lead Strategist）

```bash
# デモスクリプト起動
python scripts/demo.py --api-key $ANTHROPIC_API_KEY
```

**ポイント**:
- 「毎朝7時に自動生成される朝報です」
- 「今日の優先タスクと推奨トピックを提案」

### Step 2: コンテンツ執筆（Drafter + Guardian）

**ポイント**:
- 「Garai Tone という独自スタイルを適用」
- 「Guardian が95点以上になるまでチェック」
- 「品質が低ければ自動で修正を依頼」

### Step 3: ビジュアル生成（Designer）

**ポイント**:
- 「HyperFrames でサムネイルと動画を生成」
- 「ブランドカラーを自動適用」

### Step 4: まとめ

**ポイント**:
- 「8体のエージェントが連携して自動化」
- 「BYOK型で安心：APIキーは顧客管理」
- 「95点品質ループで妥協なし」

---

## デモコマンド集

### 基本デモ（モック）

```bash
python scripts/demo.py --mock
```

### 実APIデモ

```bash
export ANTHROPIC_API_KEY=your_key_here
python scripts/demo.py
```

### テスト実行（信頼性確認用）

```bash
pytest tests/ -v --tb=short
```

### 特定エージェントのテスト

```bash
# Drafter + Guardian ループ
pytest tests/test_integration.py::TestDrafterGuardianLoop -v

# E2E ワークフロー
pytest tests/test_e2e.py::TestDailyWorkflow -v
```

---

## トラブルシューティング

### API エラーの場合

1. モックモードに切り替え
   ```bash
   python scripts/demo.py --mock
   ```

2. 録画済みデモ動画を再生

### ネットワーク不安定の場合

1. テザリングに切り替え
2. モックモードで継続

### Python エラーの場合

```bash
# 依存関係の再インストール
pip install -e ".[dev]"
```

---

## デモ後の補足資料

### 質疑応答用

| 想定質問 | 回答 |
|---------|------|
| 価格は？ | Founding Member: 初期49,800円 + 月9,800円 |
| いつから使える？ | 2026年7月以降（Phase 1 完了後） |
| API費用は？ | 顧客が Anthropic と直接契約（BYOK） |
| 競合との違いは？ | 集客→営業→クロージング統合、95点品質ループ |
| カスタマイズは？ | ブランドDNA で完全カスタマイズ可能 |

### 参照URL

- Anthropic: https://anthropic.com
- Claude Code: https://claude.ai/code
- galaiworks: (会社サイト)

---

## チェックリスト

### デモ前日

- [ ] API キー残高確認
- [ ] デモスクリプト動作確認
- [ ] モックモード動作確認
- [ ] バックアップ動画準備

### デモ当日

- [ ] 電源・充電確認
- [ ] ネットワーク接続確認
- [ ] ターミナルフォントサイズ調整（見やすく）
- [ ] 録画ソフト準備（必要なら）

### デモ直前

- [ ] 他のアプリ終了
- [ ] 通知OFF
- [ ] ターミナルをフルスクリーンに

---

## 成功の定義

1. **技術デモ成功**: 朝報→コンテンツ→ビジュアルの流れを見せる
2. **価値伝達成功**: 「8体のエージェントが自動化」を理解してもらう
3. **差別化伝達成功**: 95点ループ、BYOK、Garai Tone の独自性
4. **興味喚起成功**: Founding Member 登録希望者を獲得

---

**Good luck at the Summit!** 🎯
