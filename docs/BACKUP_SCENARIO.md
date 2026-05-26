# バックアップシナリオ（API障害時用）

> サミット 2026/6/4 デモ用緊急対応手順

---

## 想定障害パターン

| レベル | 障害内容 | 発生確率 | 対応時間 |
|--------|----------|----------|----------|
| L1 | ネットワーク一時的不安定 | 中 | 30秒待機 |
| L2 | Anthropic API レート制限 | 低 | モック切替 |
| L3 | Anthropic API 全面障害 | 極低 | 録画再生 |
| L4 | ローカル環境障害 | 極低 | バックアップPC |

---

## L1: ネットワーク一時的不安定

### 症状
- API レスポンスが遅い
- タイムアウトエラー

### 対応手順

```bash
# 1. 30秒待機して再試行
python scripts/demo.py --api-key $ANTHROPIC_API_KEY

# 2. それでも失敗 → モックモードへ
python scripts/demo.py --mock
```

### トーク例
「ネットワークが少し不安定ですね。実際の本番環境では自動リトライ機能があります。今回はモックモードでお見せします」

---

## L2: Anthropic API レート制限

### 症状
- `429 Too Many Requests` エラー
- `rate_limit_exceeded` メッセージ

### 対応手順

```bash
# モックモードに即時切替
python scripts/demo.py --mock
```

### トーク例
「APIの利用制限に達しました。実際の運用では、Tier 1 以上のお客様は十分な枠がありますのでご安心ください。モックモードでフローをお見せします」

---

## L3: Anthropic API 全面障害

### 症状
- API が完全に応答しない
- 500 系エラーが連続

### 対応手順

1. **モックモードで継続**（推奨）
   ```bash
   python scripts/demo.py --mock
   ```

2. **録画済みデモ動画を再生**
   - 場所: `docs/demo_recording.mp4`（事前準備必須）

### トーク例
「現在 Anthropic 側で障害が発生しているようです。こういった場合に備えて、録画版をご用意しています。実際のシステムでは、障害時は自動的に人間にエスカレーションされます」

---

## L4: ローカル環境障害

### 症状
- Python エラー
- 依存関係の問題

### 対応手順

```bash
# 依存関係再インストール
pip install -e ".[dev]"

# それでも失敗 → バックアップPCへ
```

### 事前準備
- [ ] バックアップPCに同じ環境を構築
- [ ] USB メモリに録画版を保存
- [ ] スマホにも録画版を保存（最終手段）

---

## 事前チェックリスト

### 前日（6/3）

```bash
# API動作確認
python scripts/demo.py --api-key $ANTHROPIC_API_KEY

# モックモード確認
python scripts/demo.py --mock

# テスト実行
pytest tests/ -v --tb=short

# API残高確認
# Anthropic Console: https://console.anthropic.com
```

- [ ] API キー残高 $50 以上あることを確認
- [ ] モックモード動作確認
- [ ] 録画版デモ動画準備
- [ ] バックアップPC準備

### 当日（6/4）

```bash
# 朝一番で動作確認
python scripts/demo.py --mock

# 本番30分前に実API確認
python scripts/demo.py --api-key $ANTHROPIC_API_KEY
```

- [ ] 電源・充電確認
- [ ] ネットワーク接続確認（会場WiFi + テザリング両方）
- [ ] ターミナルフォントサイズ調整
- [ ] 通知OFF

---

## 緊急連絡先

| 状況 | 連絡先 |
|------|--------|
| Anthropic 障害確認 | https://status.anthropic.com |
| 技術サポート | galaiworks 携帯 |
| 会場スタッフ | 当日確認 |

---

## モックモードの仕様

モックモードでは以下が表示されます:

1. **朝報サンプル** - 事前生成された朝報
2. **コンテンツサンプル** - Garai Tone 適用済み記事
3. **評価サンプル** - Guardian 95点ループの結果

実際の API 呼び出しは行われませんが、**フローと UI は本番と同一**です。

```bash
# モックモード起動
python scripts/demo.py --mock

# 出力例
[モックモード] 朝報を生成中...
[モックモード] Drafter がコンテンツを執筆中...
[モックモード] Guardian が品質チェック中...
[モックモード] スコア: 96/100 - 承認
```

---

## 録画版デモの準備手順

### 録画ソフト
- macOS: QuickTime Player (Cmd+Shift+5)
- Windows: OBS Studio
- Linux: SimpleScreenRecorder

### 録画内容
1. ターミナルで `python scripts/demo.py` を実行
2. 朝報生成 → コンテンツ執筆 → Guardian チェック → 承認 の流れ
3. 各ステップで 3-5 秒の間を取る

### 保存場所
- `docs/demo_recording.mp4`
- バックアップ: USB メモリ、Google Drive、スマホ

---

## 成功の定義（再確認）

障害発生時でも以下が伝われば成功:

1. **8体エージェントの連携** - フロー図で説明可能
2. **95点品質ループ** - 概念を説明可能
3. **BYOK型の安心感** - セキュリティの説明
4. **Garai Tone の独自性** - サンプル文章で説明

**技術デモが完璧でなくても、価値が伝われば成功です。**

---

**Good luck at the Summit!**
