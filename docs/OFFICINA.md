# Officina — 自律型 AI エージェンシー OS(実装ドキュメント)

要件定義 `自律型AIエージェンシーOS 要件定義 v0.1` の実装。Virtus / Faber の既存資産を
再配置し、営業リサーチ → 納品 → アフターまでを自律実行する。人間の接触点を
**ICP 承認 + 2 ゲート(契約署名・納品承認)** に圧縮する。

> 本実装は Phase 1(ハイブリッド前提)。API キーが無くても全パイプラインを
> オフラインで通せる決定論実装になっており、`pytest` と
> `python scripts/officina_demo.py` で動作を確認できる。

---

## 1. 設計原則とコードの対応(要件定義 §2)

| # | 原則 | 実装箇所 |
|---|------|---------|
| 1 | 自律可能性 = 検証可能性 × 可逆性 | `pipeline.py`(各ステージに gate と人間関与レベル) |
| 2 | 各工程にテストスイート相当の合格基準 | `pipeline.py` の `gate_type`、`orchestrator._deterministic_gate` |
| 3 | オーケストレーター・ワーカー型(God Model 禁止) | `orchestrator.Orchestrator` + `agents/*` |
| 4 | 検証は独立エージェントで(生成と検証を分離) | `governance/guardian_gate.py`(生成エージェントとは別) |
| 5 | 決定論ゲートは LLM に判断させない | `governance/deterministic_gates.py`, `deliverability.py`, `permissions.py` |
| 6 | リジェクトログ = リグレッションテスト | `governance/reject_log.py` |

---

## 2. パイプライン(要件定義 §4)

`src/officina/pipeline.py` の `PIPELINE` が §4 の表をそのまま定義する。
`validate_pipeline()` が import 時に「全 12 ステージが昇順」「人間必須ゲートは
契約締結と納品承認のちょうど 2 点」を自己検証する。

```
0 ICP_RESEARCH  → 1 PROSPECTING → 2 OUTREACH → 3 QUALIFY → 4 DISCOVERY
→ 5 PROPOSAL → 6 CLOSING → 🚩7 CONTRACT → 8 BUILD → 🚩9 DELIVERY_APPROVAL
→ 10 DELIVERY → 11 AFTERCARE
```

各ステージの合格ゲート:

| ステージ | ゲート種別 | 合格基準 |
|---------|-----------|---------|
| 0 ICP | 決定論 | ソース実在性 |
| 1 Prospecting | 決定論 | データ検証率 ≥ 50% / 重複・不達除去 |
| 2 Outreach | 決定論 | deliverability 健全性 + 送信量上限 + opt-out |
| 3 Qualify | Guardian | 分類信頼度 ≥ 70% / 危険ワードは即エスカレーション |
| 4 Discovery | 決定論 | 必須項目充足 |
| 5 Proposal | 決定論 | 価格ガードレール(下限・未承認値引き禁止) |
| 6 Closing | なし | 高額は人間主導(ACV ≥ $50k で人間ゲート) |
| 🚩7 Contract | 人間 | 署名(不可逆) |
| 8 Build | 決定論 + Guardian | 受入テスト全通過 → 独立検証 |
| 🚩9 Delivery承認 | 人間 | 最終承認(不可逆) |
| 10 Delivery | 決定論 | 疎通テスト |
| 11 Aftercare | 決定論 | 課金トリガー(契約有効 + 納品受入) |

---

## 3. エージェント編成(要件定義 §5)

`src/officina/agents/` に配置。すべて `src/agents/base.BaseAgent` を継承。

| 役割 | クラス | 既存資産 | モデル階層 |
|------|--------|---------|-----------|
| Orchestrator | `Orchestrator` | Virtus: Lead Strategist | Opus |
| Scout | `Scout` | Virtus: Researcher | Sonnet |
| Prospector | `Prospector` | 新規(Clay 相当) | Haiku |
| Outreach | `Outreach` | Virtus: Distributor | Haiku |
| Qualifier | `Qualifier` | Virtus: Connector | Sonnet |
| Discovery | `Discovery` | Faber: Discovery 層 | Opus |
| Proposer | `Proposer` | Virtus: Drafter+Designer | Sonnet |
| Closer | `Closer` | 新規(補助役) | Opus |
| Architect/Builder | `ArchitectBuilder` | Faber: Architect→Builder | Opus |
| Guardian(検証層) | `GuardianGate` | Virtus: Guardian | 決定論 + Opus |
| Ops/Analyst | `Ops` | Virtus: Analyst | Sonnet |

モデル階層は `config.ModelTiers` が環境変数 `MODEL_OPUS/SONNET/HAIKU` から解決する。

---

## 4. ガバナンス 3 層(要件定義 §6)

`src/officina/governance/`:

- **§6.1 決定論ゲート層** — `deterministic_gates.py`(送信量・価格・契約・デプロイ・課金)、
  `deliverability.py`(バウンス/苦情/評価/ウォームアップ)、`permissions.py`
  (ゼロトラスト・最小スコープ。Outreach は送信のみ、Builder は本番デプロイ不可、
  `sign_contract`/`approve_delivery` は誰も実行不可)。
- **§6.2 Guardian 独立検証層** — `guardian_gate.py`。生成と検証を分離(原則 #4)。
  95 点ループ + 神さんの教え「本当に 95 点か?」の self-reflection。
- **§6.3 人間 HITL ゲート層** — `hitl.py`。契約署名(ゲート A)と納品承認(ゲート B)で
  必ず停止し、`escalation.md` の Level 1-4 で例外エスカレーション。

---

## 5. deliverability は事業継続条件(要件定義 §3 / §8.1)

「撤退の主因は到達不全」。`DeliverabilityMonitor` がバウンス率・スパム苦情率・
ドメイン評価・ウォームアップ送信量を**決定論で**監視し、閾値を超えたら
アウトリーチを即停止する。閾値は `config.OfficinaConfig` に集約(環境変数で上書き可)。

---

## 6. 実行方法

```bash
# 依存(BYOK: 実 LLM を使う場合のみ ANTHROPIC_API_KEY が必要)
pip install -e ".[dev]"

# テスト(オフライン・37 ケース)
pytest

# エンドツーエンド・デモ(API キー不要)
python scripts/officina_demo.py
```

---

## 7. §12 オープン決定事項に対する Phase 1 の既定値

要件定義 §12 は判断待ち。実装は以下の**保守的な既定値**を採用し、すべて
`config.OfficinaConfig` / `metadata` で上書きできるようにしてある(v0.2 で確定)。

1. **初期 ACV 帯** — 勝ち筋に従い低 ACV 高ボリューム。`acv_ai_led_max_usd=$25k`、
   `acv_human_required_usd=$50k`(超過はクロージング人間主導)。
2. **納品物の標準型** — 「クライアント向けエージェント構築(Faber 適用)」に絞る。
   合格基準(受入テスト)を作りやすく自律度が上がるため(`ArchitectBuilder`)。
3. **シグナル層** — 抽象化のみ実装(`Prospector` がデータ検証率・重複/不達除去を担保)。
   自前/外部連携の選択は差し込み可能な設計。
4. **法人化との接続** — 契約締結ゲート(ゲート A)= 法人名義受注の起点として整合。
5. **deliverability インフラ** — ドメイン分離・ウォームアップを決定論ゲートで内製制御。
   外部ツール連携も `DeliverabilityMetrics` の入力差し替えで可能。

> これらは**ガライの確認待ち**。回答で v0.2 に更新する。
