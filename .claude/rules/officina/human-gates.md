# Human Gates - 人間 HITL ゲート(2点のみ・第3層)

このファイルは Officina のガバナンス第3層
「人間 HITL(Human-In-The-Loop)ゲート」の詳細仕様です。

---

## 冒頭原則:逆ピラミッドのレバレッジ

Officina が目指すのは「完全無人」ではない。
目指すのは **人間 1 人が、ごく少数のゲートだけを所有する逆ピラミッド**である。

レバレッジの本質は「人間の不在」ではなく、
**「1 人:N 時間のエージェント作業」という比率**にある。
人間がゼロになることではなく、人間 1 人がエージェント群の N 時間ぶんの作業を
統括できることこそが価値だ。だから人間を消そうとしない。人間が触る点を最小化する。

ではどこに人間を置くか。判断基準は次の式に集約される:

**自律可能性 = 検証可能性 × 可逆性**

- 検証でき、かつ取り消せる行為 → エージェントに任せてよい(間違えても直せる)。
- 検証できても**取り消せない**行為 → 人間が所有する(間違いが致命的)。

ゆえに、Officina が人間に残す HITL ゲートは**不可逆な 2 点のみ**である。

- **ゲートA: 契約締結(ステージ7)** — 署名は法的に取り消せない。
- **ゲートB: 納品物 最終承認(ステージ9)** — 出荷後は賠償リスクが乗る、取り消せない。

それ以外の工程(探索・選別・提案草案・アウトリーチ・ビルド・品質チェック)は、
検証可能かつ可逆なので、エージェントが自律実行する。

---

## 人間(ガライ)が所有する全 4 点

HITL ゲートは 2 点だが、人間が関与する判断点は全部で 4 点ある。
そのうち 2 点は「不可逆ゲート」、2 点は「戦略・高額判断」である。

```yaml
human_owned_points:
  - id: 1
    name: "ICP・戦略の承認"
    reversible: true            # いつでも見直せる(可逆)
    type: "戦略判断"
    note: "誰に・何を・いくらで売るかの方針。エージェント全体の前提。"

  - id: 2
    name: "高額案件のクロージング判断"
    reversible: true            # 判断自体は可逆(署名前)
    type: "高額判断"
    note: "大型商談で進める/退くの判断。AI は条件整理・草案まで。"

  - id: 3
    name: "契約署名"
    reversible: false           # 【不可逆】法的拘束が発生
    type: "HITL ゲートA"
    note: "署名主体は常に人間(ガライ)。AI は発火不可。"

  - id: 4
    name: "納品物 最終承認"
    reversible: false           # 【不可逆】出荷後は賠償リスク
    type: "HITL ゲートB"
    note: "最終 OK は人間。AI は制作・自己点検・Guardian チェックまで。"

principle: "上記 4 点以外、人間は原則タッチしない。"
```

---

## ゲートA: 契約締結(ステージ7)【不可逆】

署名は法的に取り消せない不可逆行為。**署名主体は常に人間(ガライ)**。
AI は契約条件の整理・草案作成までしか行えない。
決定論ゲート `contract_trigger_gate` と連動し、AI による契約発火を構造的に封じる。

### トリガー条件

```yaml
gate_a_trigger:
  stage: 7
  when:
    - "Proposer/Closer が契約条件を整理し、草案が完成した"
    - "price_floor_gate を通過している(下限・値引き承認済み)"
    - "顧客が締結意思を示した"
  escalation_level: 3   # 高額案件は escalation.md Level 3(4時間以内)
```

### 人間に提示する情報

```yaml
gate_a_presented_info:
  - 契約相手・案件名
  - 契約金額・支払条件
  - 値引きの有無と承認状況(price_floor_gate 結果)
  - 契約期間・主要条項の要約(AI が整理)
  - リスク注記(賠償条項・解約条件・特殊条件)
  - 推奨アクション("署名" / "条項修正依頼" / "見送り")
  - 署名手段リンク(電子署名プロバイダ)
```

### 承認 / 差し戻し / 却下後のフロー

```yaml
gate_a_flow:
  approve_and_sign:
    actor: "人間(ガライ)のみ"
    effect: "電子署名 -> contract_trigger_gate が署名イベントを検証"
    next: "署名確認後、billing_gate 経由で課金フローへ"
  request_revision:
    effect: "Closer/Proposer に条項修正を差し戻し、再提示"
  reject:
    effect: "案件をアーカイブ。理由を学習データに反映(ICP 精緻化)"

invariant: "AI は契約 state を signed に遷移させられない(contract_trigger_gate)。"
```

---

## ゲートB: 納品物 最終承認(ステージ9)【不可逆】

納品物の出荷には賠償リスクが乗る。出荷は取り消せない不可逆行為であり、
**最終承認は人間が行う**。AI は制作・自己点検・Guardian の 95 点チェックまで。

### トリガー条件

```yaml
gate_b_trigger:
  stage: 9
  when:
    - "Builder が納品物を完成させた"
    - "Guardian が 95 点ループを通過させた(quality-95.md)"
    - "prod_deploy_gate を通過している(該当する場合)"
  escalation_level: 2   # 通常 Level 2、大型案件は Level 3
```

### 人間に提示する情報

```yaml
gate_b_presented_info:
  - 納品物の概要・対象顧客・案件名
  - Guardian 評価結果(総合点・各軸スコア・残課題)
  - テスト結果 / prod_deploy_gate の状態(該当時)
  - 想定される賠償・品質リスクの注記
  - 差分サマリー(前回承認分からの変更点)
  - 推奨アクション("承認・出荷" / "修正依頼" / "却下")
```

### 承認 / 差し戻し / 却下後のフロー

```yaml
gate_b_flow:
  approve_and_release:
    actor: "人間(ガライ)のみ"
    effect: "permission_scope_gate の deliverable.release を人間として実行"
    next: "出荷・納品完了を記録"
  request_revision:
    effect: "Builder に修正を差し戻し、Guardian 再評価 -> 再提示"
  reject:
    effect: "出荷せずアーカイブ。原因を学習データへ"

invariant: "deliverable.release は HUMAN_ONLY_ACTIONS(deterministic-gates.md)。"
```

---

## 例外エスカレーション(恒常作業ではなく例外処理)

ゲートA/B に加え、Qualifier / Proposer からの**例外エスカレーション**を人間が受ける。
これは恒常的な承認作業ではなく、あくまで「例外」が起きたときの処理である。

```yaml
exception_escalations:
  from_qualifier:
    examples:
      - "ICP から大きく外れるが極めて高スコアのリード(判断を仰ぐ)"
      - "選別ルールで判定不能な異常ケース"
    level: 2
  from_proposer:
    examples:
      - "価格下限を割る提案要求(price_floor_gate block 後)"
      - "標準テンプレートに収まらない特殊要件"
    level: 2-3

principle: |
  例外エスカレーションは「人間の常時関与」を意味しない。
  恒常作業はエージェントが処理し、例外のみ人間に上がる。
  例外が頻発する場合は ICP・ルール・スキルを更新し、例外自体を減らす
  (escalation.md の改善ループと同じ思想)。
```

---

## 非ゴール(意図的に自律しない領域)

Officina は「何でも自律化」を目指さない。
次の領域は、技術的に可能でも**意図的に自律しない**。

```yaml
non_goals:
  - name: "クロージングの完全自律化"
    reason: "高額判断は可逆でも人間が所有(human_owned_points #2)"
  - name: "契約署名の自律化"
    reason: "不可逆。ゲートA・contract_trigger_gate で構造的に封じる"
  - name: "納品物の無人出荷"
    reason: "不可逆・賠償リスク。ゲートBで人間最終承認"
  - name: "士業の独占業務に踏み込む納品"
    reason: |
      弁護士・税理士・司法書士等の独占業務(法律判断・税務申告代理等)には
      踏み込まない。compliance.md の法令遵守と整合させ、納品物は
      これら独占業務を侵さない範囲に限定する。
```

---

## Phase 計画(人間ゲートの推移)

```yaml
phase_plan:
  phase_1:
    description: "ハイブリッド前提。自律は進めるが人間ゲートを厚めに置く。"
    human_gates:
      - "ステージ6(高額判断の事前確認)を人間に置く"
      - "ステージ7(契約署名)= ゲートA、人間"
      - "ステージ9(納品最終承認)= ゲートB、人間"
    note: "立ち上げ期は検証データが薄いため、人間関与を多めに保つ。"

  intermediate:
    description: "検証データ蓄積に伴い、ステージ6 の関与を例外処理へ縮小。"

  asymptote:
    description: "漸近的な到達点。"
    permanent_human_gates:
      - "契約署名(ゲートA)【不可逆】"
      - "納品物最終承認(ゲートB)【不可逆】"
    note: |
      どれだけ自律化が進んでも、不可逆な 2 点は恒久的に人間が所有する。
      自律可能性 = 検証可能性 × 可逆性 の式により、可逆性ゼロの行為は
      永遠に人間のもの。これが Officina の設計上の漸近線である。
```

---

## 監査ログ要件

すべての人間ゲート通過は記録する。

```yaml
human_gate_log_entry:
  timestamp: "2026-06-21T14:23:45+09:00"
  customer_id: "founding_001"
  gate: "gate_a_contract_signing"     # or gate_b_deliverable_release
  stage: 7
  reversible: false
  presented_info_ref: "doc://contracts/xxx"
  agent_preparation:
    prepared_by: "Closer"
    guardian_score: 96                 # ゲートB の場合
    price_floor_gate: "passed"         # ゲートA の場合
  human_decision:
    actor: "garai"                     # 署名・承認は必ず人間
    decision: "approve"                # approve | revise | reject
    response_time: "01:12:30"
    notes: "条項確認済み、署名実行"
  downstream:
    contract_trigger_gate: "passed"    # ゲートA -> 課金フローへ
    learning_reflected: false

audit_principles:
  - "不可逆ゲートの actor は必ず人間 ID であること(AI ID は不許可)"
  - "署名・出荷イベントは改竄不能ストレージへ追記"
  - "差し戻し/却下の理由を学習データに反映し、例外を逓減させる"
```

---

## まとめ

第一に、**人間ゲートは不可逆な 2 点のみ**(契約署名・納品承認)。

第二に、**人間が触る判断は全 4 点**(ICP・高額判断・署名・納品承認)。それ以外はタッチしない。

第三に、**自律可能性 = 検証可能性 × 可逆性**。可逆性ゼロの行為は恒久的に人間のもの。

第四に、**完全無人ではなく逆ピラミッド**。1 人:N 時間のエージェント作業比率こそがレバレッジ。

人間を消すのではなく、人間が触る点を最小化する。これが Officina の HITL 設計思想である。
