"""Guardian 独立検証層(要件定義 §6.2 / quality-95.md)。"""

from __future__ import annotations

from src.officina.governance.guardian_gate import GuardianGate
from src.officina.models import Verdict


def test_clean_content_passes(brand_dna):
    g = GuardianGate(brand_dna=brand_dna)
    content = (
        "結論から言うと、AI エージェントは集客を仕組み化します。"
        "具体的には、リサーチと配信を自動化し、人間は判断に集中できます。"
    )
    r = g.evaluate(content, content_type="note_article")
    assert r.verdict == Verdict.PASS
    assert r.score is not None and r.score >= 95


def test_overpromise_fails(brand_dna):
    g = GuardianGate(brand_dna=brand_dna)
    r = g.evaluate("このサービスを使えば絶対に必ず100%成功します。", content_type="x_post")
    assert r.verdict == Verdict.FAIL
    assert r.score is not None and r.score < 95


def test_brand_forbidden_word_penalized(brand_dna):
    g = GuardianGate(brand_dna=brand_dna)
    r = g.evaluate("誰でも簡単にできる魔法のような方法をご紹介します。" * 2)
    assert r.verdict == Verdict.FAIL


def test_email_without_unsubscribe_is_critical(brand_dna):
    g = GuardianGate(brand_dna=brand_dna)
    r = g.evaluate("はじめまして。弊社サービスのご案内です。", content_type="outreach_email")
    # 配信解除動線なし = 重大違反 → 強制エスカレーション。
    assert r.verdict == Verdict.ESCALATE
    assert r.details.get("force_reject") is True


def test_compliant_email_passes(brand_dna):
    g = GuardianGate(brand_dna=brand_dna)
    content = (
        "ご担当者様\n\ngalaiworks の山田と申します。貴社の取り組みを拝見しご連絡しました。"
        "ご興味があればお打ち合わせをお願いします。\n\n"
        "送信者: galaiworks(お問い合わせ・連絡先あり)\n配信停止はこちらから解除できます。"
    )
    assert g.evaluate(content, content_type="outreach_email").verdict == Verdict.PASS
