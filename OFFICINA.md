# Officina — 自律型 AI エージェンシー OS

> 「工房・作業場」の意。営業から納品までを自律エージェントチームで回し、
> 人間(ガライ)の接触点を「2 つのゲート」に圧縮する。

[![Status: v0.2 draft](https://img.shields.io/badge/status-v0.2%20draft-yellow)]()
[![Model: Claude](https://img.shields.io/badge/model-Opus%204.8-purple)]()
[![Tests](https://img.shields.io/badge/gates-37%20passing-green)]()

---

## これは何か

Officina は、既存の **Virtus**(集客→クロージングの 8 体チーム)と **Faber**
(設計→実装層)の資産を再配置し、**営業リサーチ → アウトリーチ → 商談 → 提案 →
クロージング補助 → 【人間】契約締結 → 開発 → 【人間】納品物承認 → 納品 →
アフター** までを一気通貫で回す自律エージェンシー OS です。

前提モデルは「完全無人」ではなく **「人間 1 人が 2 ゲートを所有する逆ピラミッド」**。
人間の総作業を「ICP 承認 ＋ 2 ゲート」に最小化します。

---

## 設計の憲法(6 原則)

第一に、**自律可能性 = 検証可能性 × 可逆性**。機械で正しさを判定でき、失敗が戻せる工程ほど自律化。逆は人間ゲートへ。
第二に、**テストスイート＝決定論的ゲートの一般化**。各工程に「テストスイート相当の合格基準」を必ず定義。作れない工程は自律化しない。
第三に、**オーケストレーター・ワーカー型**(God Model 禁止)。
第四に、**検証は独立エージェントで**(生成と検証を兼務させない)。
第五に、**決定論ゲートは LLM に判断させない**。送信量・課金・契約・デプロイは `src/officina/gates.py` のハードロジックで強制。
第六に、**リジェクトログ＝リグレッションテスト**。

---

## ガバナンス 3 層

| 層 | 役割 | 実装 |
|----|------|------|
| 第 1 層 決定論ゲート | LLM に判断させないハードロジック | [`src/officina/gates.py`](./src/officina/gates.py) / [deterministic-gates.md](./.claude/rules/officina/deterministic-gates.md) |
| 第 2 層 Guardian 独立検証 | 統合前の合格基準照合・敵対的レビュー・95 点ループ・ドリフト監視 | [guardian.md](./.claude/agents/officina/guardian.md) / [quality-95.md](./.claude/rules/quality-95.md) |
| 第 3 層 人間 HITL ゲート | 契約締結・納品承認の 2 点(不可逆) | [human-gates.md](./.claude/rules/officina/human-gates.md) |

全体像は [governance.md](./.claude/rules/officina/governance.md) を参照。

---

## エージェント編成(13 体)

ゼロから作らず、既存ロスターを再配置。

| 役割 | 由来 | モデル階層 | 定義 |
|------|------|-----------|------|
| Orchestrator | Virtus: Lead Strategist | Opus 4.8 | [orchestrator.md](./.claude/agents/officina/orchestrator.md) |
| Scout(ステージ0) | Virtus: Researcher | Sonnet＋web | [scout.md](./.claude/agents/officina/scout.md) |
| Prospector(1) | 新規(Clay 相当) | Sonnet/Haiku＋データ API | [prospector.md](./.claude/agents/officina/prospector.md) |
| Outreach(2) | Virtus: Distributor | Haiku＋テンプレ | [outreach.md](./.claude/agents/officina/outreach.md) |
| Qualifier(3) | Virtus: Connector | Sonnet | [qualifier.md](./.claude/agents/officina/qualifier.md) |
| Discovery(4) | Faber: Discovery 層 | Opus 4.8 | [discovery.md](./.claude/agents/officina/discovery.md) |
| Proposer(5) | Virtus: Drafter＋Designer | Sonnet＋galai-tone | [proposer.md](./.claude/agents/officina/proposer.md) |
| Closer(6) | 新規(補助役) | Opus 4.8(補助のみ) | [closer.md](./.claude/agents/officina/closer.md) |
| Architect(8) | Faber: Architect | Opus 4.8＋xhigh | [architect.md](./.claude/agents/officina/architect.md) |
| Builder(8) | Faber: Builder | Opus 4.8＋ultracode | [builder.md](./.claude/agents/officina/builder.md) |
| Guardian | Virtus: Guardian | 決定論＋Opus 検証 | [guardian.md](./.claude/agents/officina/guardian.md) |
| Delivery(10) | 新規 | Sonnet | [delivery.md](./.claude/agents/officina/delivery.md) |
| Ops/Analyst(11) | Virtus: Analyst | Sonnet＋決定論 | [ops-analyst.md](./.claude/agents/officina/ops-analyst.md) |

> 階層化(Opus は判断、Haiku/Sonnet はワーカー)が大規模でもコストを制御する主レバー。

---

## パイプライン(11 ステージ ＋ 2 人間ゲート)

詳細は [pipeline.md](./.claude/rules/officina/pipeline.md) / コード正本は
[`src/officina/pipeline.py`](./src/officina/pipeline.py)。

```
0 ICP/市場    →1 リスト/エンリッチ →2 アウトリーチ →3 トリアージ
→4 要件抽出   →5 提案/見積        →6 クロージング補助
→ 🚩7 契約締結(人間・署名・不可逆)
→8 設計/実装/検証 → 🚩9 納品物承認(人間・検証・不可逆)
→10 納品/オンボ  →11 アフター(請求/保守/拡張)
```

---

## 人間(ガライ)が所有する 4 点

1. **ICP・戦略の承認**(ステージ0)
2. **高額案件のクロージング判断**(ステージ6)
3. **契約署名**(ゲート A・必須・不可逆)
4. **納品物の最終承認**(ゲート B・必須・不可逆)

それ以外(リサーチ・送信・トリアージ・要件抽出・開発・検証・請求・保守)は原則タッチしない。

### 非ゴール(意図的に自律しない)
- クロージングの完全自律化(AI は補助まで)
- 契約署名の自律化(法的に取り消せない)
- 納品物の無人出荷(賠償リスク)
- 士業の独占業務に踏み込む納品(有資格者の関与必須)

---

## グローバル勝ち筋(モデリング根拠 / 2026年6月時点)

- **ハイブリッドが売上で勝つ**(純 AI 比 約 2.3 倍)。純 AI はクローズドウォンで約 22 ポイント劣後。
- **撤退の主因は到達不全**。過剰送信でドメイン崩壊し試行の約 47% が 90 日で頭打ち。deliverability は前提。
- **成否の 80〜90% はデータ・ルーティング・ガードレール**(プロンプトは 10〜20%)。シグナル層が本丸。
- **ACV 閾値**: $25k 未満の単純意思決定は AI 主導が機能、$50k 超・複数ステークホルダーは人間必須。
- **本番運用コスト**: エージェント 1 体あたり 0.25〜0.5 人月/継続。"作って放置" が最大の死因。

---

## v0.2 作業前提(要件定義 §12 への暫定回答)

> 以下は v0.1 §12 のオープン論点に対し、勝ち筋に沿った **暫定デフォルト**を置いたもの。
> ガライの判断で上書き可能。確定したら本セクションを更新する。

| # | 論点 | 暫定デフォルト(v0.2) | 根拠 |
|---|------|---------------------|------|
| 1 | 初期 ACV 帯 | **低 ACV・高ボリューム**から開始 | 勝ち筋は前者。合格ゲートが作りやすく自律度を上げやすい |
| 2 | 納品物の標準型 | **クライアント向けエージェント構築(Faber 適用)に絞る** | 絞るほど受入基準(テスト)が作りやすく自律度が上がる |
| 3 | シグナル層 | Phase 1 は**外部データ連携**で立ち上げ、検証後に自前比率を上げる | 80-90% の最優先投資だが、まず疎通を取る |
| 4 | 法人化との接続 | 契約締結ゲート=法人名義受注を**前提に組み込む** | 締結前に設立するロジックと整合 |
| 5 | deliverability インフラ | Phase 1 は**専用ツール＋ `deliverability_gate` の二重化** | 事業継続条件のため内製を待たず先に守る |

これらは「決定」ではなく「進めるための仮置き」です。1〜5 のどれを変えても、本リポジトリの構造(ゲート・パイプライン・エージェント定義)はそのまま使えます。

---

## リポジトリ構造(Officina 部分)

```
OFFICINA.md                                  # このファイル(正本の入口)
docs/officina/REQUIREMENTS.md                # 要件定義書 v0.1(原文)
src/officina/
├── __init__.py
├── gates.py                                 # 決定論ゲート(ハードロジック・正本)
├── base.py                                  # BaseAgent(ゲート連携・合格ゲート)
└── pipeline.py                              # 11 ステージ定義(正本)
tests/officina/
├── test_gates.py                            # 決定論ゲートの回帰テスト(28 件)
└── test_pipeline.py                         # パイプライン不変条件(9 件)
.claude/agents/officina/                     # 13 体エージェント定義
.claude/rules/officina/
├── governance.md                            # 3 層ガバナンス全体像
├── pipeline.md                              # パイプライン詳細
├── deterministic-gates.md                   # 第 1 層詳細
├── deliverability.md                        # 到達性(事業継続条件)
└── human-gates.md                           # 第 3 層(人間ゲート 2 点)
```

---

## 開発の始め方

```bash
# テスト(決定論ゲートとパイプライン不変条件)
python -m pytest tests/officina/ -q

# パッケージの利用
PYTHONPATH=src python -c "from officina import gates; \
print(gates.send_volume_gate({'domain_age_days':3,'sent_today':10}, 15))"
```

決定論ゲートは外部依存ゼロで単体テスト可能です。エージェント定義は
`.claude/agents/officina/` を Claude Code が自動認識します。

---

## Phase 計画

- **Phase 1(今すぐ)**: ハイブリッド前提。ステージ 0-5 ＋ 8-11 を自律、6-7・9 を人間。低 ACV から 1 案件で全工程を通す。
- **Phase 2**: 例外エスカレーション率を下げ、人間関与を例外のみに。
- **Phase 3**: 低額・単純クロージングの一部を AI 主導に拡張(署名は人間維持)。
- **asymptote**: 人間ゲートは契約署名と納品承認の 2 点に固定(恒久)。

---

Proprietary. galaiworks 独自 IP(Garai Tone、DREAM WRITING、IMPACT v2.0R)を含む。
