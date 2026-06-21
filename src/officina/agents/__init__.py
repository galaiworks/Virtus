"""Officina エージェント編成(要件定義 §5)。

ゼロから作らず、Virtus / Faber の既存ロスターを再配置する。各エージェントは
``src.agents.base.BaseAgent`` を継承し、決定論的にオフライン実行できる
``execute()`` を持つ(API キー無しでもパイプラインを通せる)。
"""

from src.officina.agents.architect import ArchitectBuilder
from src.officina.agents.closer import Closer
from src.officina.agents.delivery import Delivery
from src.officina.agents.discovery import Discovery
from src.officina.agents.ops import Ops
from src.officina.agents.outreach import Outreach
from src.officina.agents.proposer import Proposer
from src.officina.agents.prospector import Prospector
from src.officina.agents.qualifier import Qualifier
from src.officina.agents.scout import Scout

__all__ = [
    "Scout",
    "Prospector",
    "Outreach",
    "Qualifier",
    "Discovery",
    "Proposer",
    "Closer",
    "ArchitectBuilder",
    "Delivery",
    "Ops",
]
