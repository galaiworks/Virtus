"""監査可能なロギング。

設計原則 #6 / quality-95.md / compliance.md が要求する「監査可能なログ」を提供する。
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def get_logger(name: str = "officina") -> logging.Logger:
    """Officina 共通ロガーを返す。"""
    global _CONFIGURED
    logger = logging.getLogger(name)
    if not _CONFIGURED:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        root = logging.getLogger("officina")
        root.addHandler(handler)
        root.setLevel(getattr(logging, level, logging.INFO))
        root.propagate = False
        _CONFIGURED = True
    return logger
