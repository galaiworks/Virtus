# Quality 95 - 95 点品質ループ詳細仕様

このファイルは Guardian の 95 点ループの詳細仕様です。
神さんの教え「逃げるな、95 点に大丈夫?と聞き返せ」を実装に反映しています。

---

## 基本原則

第一に、**95 点未満は絶対に APPROVED しない**。

第二に、**自分自身に問い返す**:「これで本当に 95 点ですか?」

第三に、**3 回の再試行で改善されない場合は人間にエスカレーション**。

第四に、**監査可能なログを残す**。

---

## 評価マトリクス

| 軸 | 配点 | 評価方法 |
|----|------|---------|
| ブランドDNA遵守 | 25 | voice、vocabulary、forbidden 一致度 |
| 法令遵守 | 25 | 全法令・規約チェック結果 |
| 内容の質 | 20 | 論理性、有用性、独自性、具体性 |
| ターゲット適合 | 15 | 想定読者への適合度 |
| 過剰約束チェック | 10 | リスク表現の検出 |
| ハルシネーション検出 | 5 | 事実誤認の有無 |

合計 100 点

---

## 各軸の詳細評価ロジック

### 1. ブランドDNA遵守(25 点)

```python
def evaluate_brand_dna_compliance(content, brand_dna):
    score = 25
    issues = []
    
    # voice チェック(8 点)
    actual_voice = analyze_voice_signature(content)
    voice_match = compare_with_brand_voice(actual_voice, brand_dna.voice)
    
    if voice_match < 0.7:
        score -= 8
        issues.append("voice 大幅不一致")
    elif voice_match < 0.85:
        score -= 4
        issues.append("voice 一部不一致")
    
    # vocabulary チェック(7 点)
    forbidden_used = find_forbidden_words(content, brand_dna.forbidden)
    if forbidden_used:
        score -= len(forbidden_used) * 3.5
        issues.append(f"禁止語使用: {forbidden_used}")
    
    preferred_used_count = count_preferred_phrases(content, brand_dna.voice.preferred)
    if preferred_used_count == 0:
        score -= 2
        issues.append("好み表現の使用なし")
    
    # tone チェック(5 点)
    tone_match = analyze_tone_match(content, brand_dna.voice.tone)
    if tone_match < 0.7:
        score -= 5
        issues.append("tone 不一致")
    
    # signature_phrases チェック(5 点)
    if len(content) > 800:  # 長文の場合
        if not has_signature_phrase(content, brand_dna.voice.signature_phrases):
            score -= 3
            issues.append("シグネチャフレーズなし")
    
    return {
        "score": max(0, score),
        "max": 25,
        "issues": issues,
    }
```

### 2. 法令遵守(25 点)

`compliance.md` の `comprehensive_compliance_check` を呼び出し。

```python
def evaluate_legal_compliance(content, content_type, customer_info):
    compliance_result = comprehensive_compliance_check(
        content, content_type, customer_info
    )
    
    if compliance_result.verdict == "CRITICAL_VIOLATION":
        return {
            "score": 0,  # 重大違反は 0 点
            "max": 25,
            "issues": [v.description for v in compliance_result.violations],
            "force_reject": True,  # 強制リジェクト
        }
    
    score = 25 - compliance_result.score_deduction
    
    return {
        "score": max(0, score),
        "max": 25,
        "issues": [v.description for v in compliance_result.violations],
    }
```

### 3. 内容の質(20 点)

```python
def evaluate_content_quality(content, content_type):
    score = 20
    issues = []
    
    # 論理性(5 点)
    if not has_clear_thesis(content):
        score -= 3
        issues.append("主張が不明確")
    
    if not has_logical_flow(content):
        score -= 2
        issues.append("論理の流れが弱い")
    
    # 有用性(5 点)
    if not has_actionable_info(content):
        score -= 5
        issues.append("読者が行動できる情報がない")
    
    # 独自性(5 点)
    similarity_score = check_similarity_to_generic_content(content)
    if similarity_score > 0.8:
        score -= 5
        issues.append("ありきたりすぎる")
    elif similarity_score > 0.6:
        score -= 2
        issues.append("やや一般的")
    
    # 具体性(5 点)
    concrete_examples_count = count_concrete_examples(content)
    if content_type in ["note_article", "proposal"] and concrete_examples_count == 0:
        score -= 5
        issues.append("具体例なし")
    elif concrete_examples_count < 2 and content_type == "note_article":
        score -= 2
        issues.append("具体例不足")
    
    return {
        "score": max(0, score),
        "max": 20,
        "issues": issues,
    }
```

### 4. ターゲット適合(15 点)

```python
def evaluate_target_fit(content, target_audience):
    score = 15
    issues = []
    
    # 用語レベルの適合(5 点)
    vocabulary_level = analyze_vocabulary_complexity(content)
    expected_level = target_audience.vocabulary_level
    
    if abs(vocabulary_level - expected_level) > 2:
        score -= 5
        issues.append(f"用語レベル不適合(現:{vocabulary_level}, 期待:{expected_level})")
    
    # 関心トピックの適合(5 点)
    topic_relevance = check_topic_relevance(content, target_audience.interests)
    if topic_relevance < 0.6:
        score -= 5
        issues.append("関心トピックから離れている")
    
    # 解決する課題の適合(5 点)
    pain_match = check_pain_alignment(content, target_audience.pain_points)
    if pain_match < 0.7:
        score -= 5
        issues.append("ターゲットの痛みに刺さっていない")
    
    return {
        "score": max(0, score),
        "max": 15,
        "issues": issues,
    }
```

### 5. 過剰約束チェック(10 点)

```python
RISK_EXPRESSIONS = [
    ("100%", 5),
    ("絶対", 5),
    ("必ず", 4),
    ("完全", 3),
    ("誰でも", 3),
    ("簡単に", 2),
    ("業界No.1", 5),  # 根拠なき場合
    ("世界一", 5),
    ("圧倒的", 2),  # 根拠なき場合
]

def evaluate_overpromise(content):
    score = 10
    issues = []
    
    for expression, penalty in RISK_EXPRESSIONS:
        if expression in content:
            # 根拠付きかチェック
            if not has_evidence_for_claim(content, expression):
                score -= penalty
                issues.append(f"過剰約束: {expression}")
    
    return {
        "score": max(0, score),
        "max": 10,
        "issues": issues,
    }
```

### 6. ハルシネーション検出(5 点)

```python
def evaluate_hallucination(content):
    score = 5
    issues = []
    
    # 引用された統計・数字のソース確認
    cited_stats = extract_statistics(content)
    for stat in cited_stats:
        if not has_source(stat):
            score -= 1
            issues.append(f"ソースなしの統計: {stat}")
    
    # 海外事例の正確性
    foreign_cases = extract_foreign_cases(content)
    for case in foreign_cases:
        if not verify_factual_accuracy(case):
            score -= 2
            issues.append(f"事実誤認の可能性: {case}")
    
    return {
        "score": max(0, score),
        "max": 5,
        "issues": issues,
    }
```

---

## 95 点ループ実装

```python
class GuardianQualityLoop:
    THRESHOLD = 95
    MAX_RETRIES = 3
    
    async def evaluate_with_loop(
        self,
        content,
        agent_name,
        content_type,
        customer_id,
    ):
        """
        95 点ループ実行
        """
        retry_count = 0
        current_content = content
        evaluation_history = []
        
        while retry_count <= self.MAX_RETRIES:
            evaluation = await self.evaluate(
                current_content,
                content_type,
                customer_id,
            )
            evaluation_history.append(evaluation)
            
            # 重大違反は即停止
            if evaluation.force_reject:
                self.escalate_to_human(
                    content=current_content,
                    reason="critical_violation",
                    history=evaluation_history,
                )
                return None
            
            # 95 点以上なら承認
            if evaluation.total_score >= self.THRESHOLD:
                # ★ 神さんの教えを実装: 自分に問い返す
                if not await self.self_reflection(
                    current_content,
                    evaluation,
                ):
                    # 自己反省で 95 点未満と判断
                    feedback = "自己反省により再評価"
                    current_content = await self.request_revision(
                        agent_name,
                        current_content,
                        feedback,
                    )
                    retry_count += 1
                    continue
                
                self.log_approval(
                    current_content,
                    evaluation,
                    history=evaluation_history,
                )
                return current_content
            
            # 95 点未満は改善指示を該当エージェントに戻す
            feedback = self.generate_specific_feedback(evaluation)
            current_content = await self.request_revision(
                agent_name,
                current_content,
                feedback,
            )
            retry_count += 1
        
        # 3 回再試行しても 95 点に到達しない場合
        self.escalate_to_human(
            content=current_content,
            reason="max_retries_exceeded",
            history=evaluation_history,
        )
        return None
    
    async def self_reflection(self, content, evaluation):
        """
        神さんの教え:「これで本当に 95 点ですか?」と自分に問い返す
        """
        reflection_prompt = f"""
あなたは Virtus の Guardian です。

以下のコンテンツを評価し、{evaluation.total_score}/100 点としました。

しかし、本当に 95 点以上ですか?
「ぱっと見で問題ない」レベルでは不十分です。
細部まで厳しく見直し、本当に承認すべきか判断してください。

特にチェックすべき点:
- 顧客のブランドDNAと完全に一致しているか?
- 一文でも「自分らしくない」表現はないか?
- 過剰約束、誇張、煽りはないか?
- 法令違反のリスクは皆無か?
- 読者の心を本当に動かすか?

判断:
- "approve" (本当に 95 点以上)
- "reject" (実は 95 点未満)
- "needs_review" (微妙、人間判断が必要)

理由も明記してください。
"""
        
        result = await self.llm_call(reflection_prompt, content)
        return result.judgment == "approve"
```

---

## 改善指示の生成

具体的・実行可能な改善指示を生成。

```python
def generate_specific_feedback(evaluation):
    """
    曖昧な指示ではなく、具体的な修正箇所を指示
    """
    feedback_parts = []
    
    for axis_eval in evaluation.axis_evaluations:
        if axis_eval.score < axis_eval.max * 0.9:
            for issue in axis_eval.issues:
                # 具体的な修正案
                specific_suggestion = generate_concrete_suggestion(
                    issue,
                    evaluation.content,
                )
                feedback_parts.append(specific_suggestion)
    
    return "\n".join(feedback_parts)


def generate_concrete_suggestion(issue, content):
    """
    例:
    "voice 不一致" → "第3段落の『〜と思います』を『〜です』に変更"
    "禁止語使用: ['絶対']" → "第5段落の『絶対に成功』を『高い確率で成功』に変更"
    """
    # LLM に具体化を依頼
    ...
```

---

## エスカレーション基準

人間判断にエスカレーションするケース:

```python
ESCALATION_TRIGGERS = {
    "critical_violation": "重大法令違反検出",
    "max_retries_exceeded": "3 回再試行しても 95 点未到達",
    "ambiguous_judgment": "Guardian が判断に迷った",
    "high_value_content": "重要コンテンツ(月次レビュー、提案書等)",
    "first_time_pattern": "未知のパターン検出",
}
```

エスカレーション通知:

```yaml
notification_channels:
  primary: Slack
  secondary: メール
  emergency: SMS
```

---

## ログ・監査

```python
def log_evaluation(content, evaluation, customer_id):
    """
    すべての評価結果を記録
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "customer_id": customer_id,
        "content_id": generate_content_id(content),
        "content_type": evaluation.content_type,
        "agent": evaluation.source_agent,
        "evaluation": {
            "total_score": evaluation.total_score,
            "verdict": evaluation.verdict,
            "axis_scores": evaluation.axis_evaluations,
            "issues": evaluation.all_issues,
        },
        "self_reflection_result": evaluation.self_reflection,
        "retry_count": evaluation.retry_count,
    }
    
    save_to_audit_log(log_entry)
```

---

## 月次品質レポート

```yaml
# 月次品質サマリー(Founding Member へ提供)

period: "2026-05-01 to 2026-05-31"
customer_id: "founding_001"

overall_metrics:
  total_evaluations: 247
  approved: 220
  rejected_then_revised: 25
  escalated_to_human: 2
  approval_rate_first_try: 0.89

quality_trend:
  - week_1: "average 91 points"
  - week_2: "average 93 points"
  - week_3: "average 94 points"
  - week_4: "average 95 points"

top_issues:
  - "voice 一部不一致(15 件)"
  - "具体例不足(8 件)"
  - "ターゲット適合度不足(5 件)"

improvements_made:
  - "voice 学習データ追加"
  - "具体例パターンの拡充"

next_month_focus:
  - "voice の精度をさらに向上"
  - "業界特化トピックの強化"
```

これにより、Founding Member は**自分のコンテンツが品質的に向上していることを毎月確認**できます。
