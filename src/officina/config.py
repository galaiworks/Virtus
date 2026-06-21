"""Officina 設定。環境変数から安全なデフォルト付きで読み込む。

決定論ゲートの閾値はすべてここに集約する。LLM ではなく設定値で制御する
(設計原則 #5「決定論ゲートは LLM に判断させない」)。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelTiers:
    """コスト最適化のためのモデル階層(要件定義 §5)。

    Opus は判断・オーケストレーション、Sonnet/Haiku はワーカー。
    """

    opus: str = field(default_factory=lambda: os.environ.get("MODEL_OPUS", "claude-opus-4-8"))
    sonnet: str = field(
        default_factory=lambda: os.environ.get("MODEL_SONNET", "claude-sonnet-4-6")
    )
    haiku: str = field(
        default_factory=lambda: os.environ.get("MODEL_HAIKU", "claude-haiku-4-5-20251001")
    )

    def resolve(self, tier: str) -> str:
        """``"opus"`` / ``"sonnet"`` / ``"haiku"`` をモデル ID へ解決する。"""
        return {"opus": self.opus, "sonnet": self.sonnet, "haiku": self.haiku}.get(
            tier.lower(), self.sonnet
        )


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _bool_env(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class OfficinaConfig:
    """OS 全体の設定。"""

    customer_id: str = "founding_001"
    dry_run: bool = False

    # --- Guardian 95 点ループ ---
    quality_threshold: int = 95
    max_retries: int = 3

    # --- ACV 帯(要件定義 §3 / §12-1) ---
    # $25k 未満・単純意思決定なら AI 主導。超過は人間必須。
    acv_ai_led_max_usd: float = 25_000.0
    acv_human_required_usd: float = 50_000.0

    # --- アウトリーチ決定論ゲート(deliverability が事業継続条件・§3/§8.1) ---
    daily_send_limit: int = 200  # 1 ドメイン/日の送信上限
    per_recipient_touch_limit: int = 4  # 同一宛先への接触回数上限
    warmup_daily_increment: int = 20  # ウォームアップ 1 日あたりの増分
    warmup_initial_limit: int = 20  # ウォームアップ初日の上限
    bounce_rate_threshold: float = 0.03  # バウンス率上限(3%)
    complaint_rate_threshold: float = 0.001  # スパム苦情率上限(0.1%)
    domain_reputation_floor: float = 70.0  # ドメイン評価スコア下限(0-100)

    # --- 価格ガードレール(§6.1) ---
    price_floor_usd: float = 0.0  # 受託下限価格(顧客実勢で設定)
    max_discount_pct: float = 0.15  # 承認なしで許す値引き上限(15%)

    # --- リジェクトログ/監査 ---
    brain_dir: str = "./brain"
    logs_dir: str = "./logs"

    models: ModelTiers = field(default_factory=ModelTiers)


def load_config() -> OfficinaConfig:
    """環境変数から ``OfficinaConfig`` を構築する。"""
    return OfficinaConfig(
        customer_id=os.environ.get("CUSTOMER_ID", "founding_001"),
        dry_run=_bool_env("DRY_RUN", False),
        quality_threshold=_int_env("QUALITY_THRESHOLD", 95),
        max_retries=_int_env("MAX_RETRIES", 3),
        acv_ai_led_max_usd=_float_env("ACV_AI_LED_MAX_USD", 25_000.0),
        acv_human_required_usd=_float_env("ACV_HUMAN_REQUIRED_USD", 50_000.0),
        daily_send_limit=_int_env("DAILY_SEND_LIMIT", 200),
        per_recipient_touch_limit=_int_env("PER_RECIPIENT_TOUCH_LIMIT", 4),
        warmup_daily_increment=_int_env("WARMUP_DAILY_INCREMENT", 20),
        warmup_initial_limit=_int_env("WARMUP_INITIAL_LIMIT", 20),
        bounce_rate_threshold=_float_env("BOUNCE_RATE_THRESHOLD", 0.03),
        complaint_rate_threshold=_float_env("COMPLAINT_RATE_THRESHOLD", 0.001),
        domain_reputation_floor=_float_env("DOMAIN_REPUTATION_FLOOR", 70.0),
        price_floor_usd=_float_env("PRICE_FLOOR_USD", 0.0),
        max_discount_pct=_float_env("MAX_DISCOUNT_PCT", 0.15),
        brain_dir=os.environ.get("BRAIN_DIR", "./brain"),
        logs_dir=os.environ.get("LOGS_DIR", "./logs"),
    )
