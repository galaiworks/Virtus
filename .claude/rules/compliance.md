# Compliance Rules - 法令遵守ガイドライン

このファイルは Virtus が遵守する法令・規約のガイドラインです。
Guardian エージェントが評価時に必ず参照します。

---

## 1. 特定電子メール法(電子メール広告)

### 適用対象
営業目的で送信されるメール、メルマガ、LINE 配信。

### 必須要件

第一に、**送信者情報の明示**
```
- 送信者の氏名または名称
- 送信者の住所
- 送信者の問合せ先(メールアドレスまたは URL)
```

第二に、**配信解除動線**
```
- 解除手順を明示
- 解除リンクをメール内に必須配置
- 解除後は速やかに送信停止
```

第三に、**事前承諾**
```
- オプトイン方式(同意した人のみに送信)
- 名刺交換等で取得した連絡先も同意確認推奨
```

### Guardian チェックロジック

```python
def check_specified_email_law(content):
    violations = []
    
    if not has_sender_info(content):
        violations.append(CriticalViolation("送信者情報がない"))
    
    if not has_unsubscribe_link(content):
        violations.append(CriticalViolation("解除動線がない"))
    
    if not has_unsubscribe_instruction(content):
        violations.append(MajorViolation("解除手順が不明"))
    
    return violations
```

---

## 2. 景品表示法(景表法)

### 適用対象
すべての商品・サービス広告(コンテンツ、SNS 投稿、LP、広告等)。

### 禁止事項

第一に、**優良誤認表示**
```
- 実際よりも著しく優良であるかのような表示
- 例: 「業界 No.1」(実態のない場合)
- 例: 「世界初」(同種既存サービスがある場合)
```

第二に、**有利誤認表示**
```
- 実際よりも有利であるかのような表示
- 例: 「他社より安い」(実態のない比較)
- 例: 「期間限定」(常時実施)
```

### NG 表現リスト

```python
EXCESSIVE_CLAIMS = [
    # 数値関連
    "100%",
    "絶対",
    "必ず",
    "完全",
    
    # 順位関連(根拠なき場合)
    "業界No.1",
    "業界トップ",
    "世界最高",
    "日本一",
    
    # 効果関連
    "誰でも稼げる",
    "簡単に成功",
    "魔法のような",
    "夢のような",
    
    # 比較関連(根拠なき場合)
    "他社より圧倒的",
    "他では真似できない",
]
```

### 推奨される代替表現

```python
ALTERNATIVES = {
    "100%": "圧倒的に",
    "絶対": "高い確率で",
    "必ず": "ほぼ確実に",
    "誰でも稼げる": "適切な実践により収益向上が期待できる",
    "業界No.1": "ITreview Grid Award 2026 Spring AIエージェントツール部門 Leader 等の評価実績あり",
}
```

---

## 3. 薬機法(医薬品医療機器等法)

### 適用対象
健康・美容・医療系のコンテンツ。

### 禁止事項

第一に、**医薬品的な効果の表現**
```
- 病気の治療・予防効果の暗示
- 例: 「○○が治る」「○○予防に効く」
```

第二に、**医療機器的な効果の表現**
```
- 機器の医療効果を暗示
- 例: 「血流改善」「痩身効果」(医療機器でない場合)
```

### Guardian チェック

```python
def check_pharma_law(content, customer_industry):
    if customer_industry not in HEALTH_RELATED_INDUSTRIES:
        return []  # 健康関連でなければスキップ
    
    violations = []
    
    medical_claims = detect_medical_claims(content)
    if medical_claims:
        violations.append(CriticalViolation(
            "薬機法違反の疑い",
            details=medical_claims,
        ))
    
    return violations
```

---

## 4. 著作権法

### 必須要件

第一に、**他者コンテンツの引用**
```
- 引用部分を明確に区別(引用符、ブロック引用等)
- 出典を明示
- 主従関係を保つ(自分の文章が主、引用が従)
- 必要最小限の引用に留める
```

第二に、**画像・動画の使用**
```
- 自作またはライセンスを取得した素材のみ使用
- フリー素材も利用規約を確認
- 有名キャラクター、商標は使用禁止
```

第三に、**生成 AI の出力**
```
- 学習元の著作権配慮
- 既存著作物との類似に注意
```

---

## 5. 個人情報保護法

### 必須要件

第一に、**取得・利用目的の明示**
```
- 個人情報を取得する際は目的を明示
- 目的外利用は同意必須
```

第二に、**安全管理措置**
```
- 漏洩防止
- アクセス制限
- 不要になったら削除
```

第三に、**第三者提供の制限**
```
- 同意なしの第三者提供禁止
- ただし業務委託は除く
```

### Virtus における個人情報の扱い

```yaml
collected_data:
  - 顧客の連絡先(契約のため)
  - 顧客のブランドDNA(サービス提供のため)
  - 顧客の業務データ(エージェント実行のため)

storage:
  location: 顧客のローカル環境(.env, brain/)
  galaiworks_server: 永続保存しない
  encryption: at-rest, in-transit

retention:
  contract_period: 契約中
  post_contract: 6 ヶ月、その後完全削除
```

---

## 6. 各プラットフォーム規約

### X(Twitter)

```yaml
prohibited:
  - 自動化された大量フォロー
  - 自動化された大量 DM
  - スパム的な投稿
  - 偽情報の拡散
  
required:
  - 公式 API 経由
  - ボット表示(必要に応じて)
  - 利用規約遵守
```

### Instagram

```yaml
prohibited:
  - 自動化されたいいね・フォロー
  - 偽の DM 大量送信
  - 著作権侵害
  
required:
  - Graph API 経由
  - ビジネスアカウント必須
```

### LinkedIn

```yaml
prohibited:
  - 連絡先の無断スクレイピング
  - 自動化されたコネクション申請
  - スパム的なメッセージ
  
required:
  - Marketing API 経由
  - 専門的な内容に限定
```

---

## 7. Guardian 評価フロー

```python
def comprehensive_compliance_check(content, content_type, customer_info):
    """
    全法令・規約チェック
    """
    all_violations = []
    
    # 1. 特定電子メール法
    if content_type in ["email", "newsletter", "line_broadcast"]:
        all_violations.extend(check_specified_email_law(content))
    
    # 2. 景表法
    all_violations.extend(check_advertisement_law(content))
    
    # 3. 薬機法
    all_violations.extend(check_pharma_law(
        content,
        customer_info.industry,
    ))
    
    # 4. 著作権法
    all_violations.extend(check_copyright(content))
    
    # 5. 個人情報保護法
    all_violations.extend(check_privacy_law(content))
    
    # 6. プラットフォーム規約
    if content_type.startswith("x_"):
        all_violations.extend(check_x_terms(content))
    elif content_type.startswith("instagram_"):
        all_violations.extend(check_instagram_terms(content))
    elif content_type.startswith("linkedin_"):
        all_violations.extend(check_linkedin_terms(content))
    
    # 重大違反は即停止
    critical = [v for v in all_violations if v.severity == "CRITICAL"]
    if critical:
        return ComplianceResult(
            passed=False,
            verdict="CRITICAL_VIOLATION",
            violations=critical,
        )
    
    # 重要違反は減点
    major = [v for v in all_violations if v.severity == "MAJOR"]
    minor = [v for v in all_violations if v.severity == "MINOR"]
    
    score_deduction = len(major) * 5 + len(minor) * 1
    
    return ComplianceResult(
        passed=score_deduction <= 5,  # 5 点以下なら通過
        verdict="PASSED" if score_deduction <= 5 else "REJECTED",
        violations=major + minor,
        score_deduction=score_deduction,
    )
```

---

## 8. 違反検出時のフロー

```
重大違反検出
    ↓
即時人間エスカレーション
    ↓
配信停止
    ↓
顧客への報告
    ↓
ブランドDNA・スキル更新で再発防止

重要違反検出
    ↓
Drafter/Connector に差し戻し
    ↓
修正版を再度 Guardian チェック

軽微違反検出
    ↓
配点で減点
    ↓
95 点ループの中で対応
```

---

## 9. 監査ログ要件

すべての Guardian チェック結果は記録:

```yaml
audit_log_entry:
  timestamp: "2026-05-15T10:23:45+09:00"
  agent: "Drafter"
  content_type: "outreach_email"
  customer_id: "founding_001"
  content_id: "content_xxx"
  
  guardian_evaluation:
    score: 92
    verdict: "REJECTED"
    
  compliance_check:
    overall: "PASSED"
    details:
      specified_email_law: "PASSED"
      advertisement_law: "MINOR_VIOLATION"
      copyright: "PASSED"
      privacy: "PASSED"
      platform_terms: "PASSED"
  
  retry_count: 1
  final_status: "approved" or "escalated"
```

これにより:
- 月次でコンプライアンス違反パターンが見える
- 改善が必要な領域がわかる
- 法的監査時に提示可能
