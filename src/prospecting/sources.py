"""能動営業のための情報ソース.

公式 RSS / API のみ利用 (スクレイピング・ブラウザ自動化は禁止).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

USER_AGENT = "Virtus/0.1 (+https://galaiworks.com; contact:galaiworks@gmail.com)"

PRTIMES_RSS_URL = "https://prtimes.jp/index.rdf"

_NAMESPACES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss": "http://purl.org/rss/1.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "atom": "http://www.w3.org/2005/Atom",
}


@dataclass(frozen=True)
class PressRelease:
    """プレスリリースの正規化形式."""

    source_id: str  # ソース内のユニーク ID (URL を使う)
    title: str
    description: str
    url: str
    published_at: datetime
    company: str | None = None
    categories: tuple[str, ...] = field(default_factory=tuple)


class ProspectingSource(ABC):
    """情報ソースの抽象基底クラス."""

    name: str = "abstract"

    @abstractmethod
    def fetch(self, period_hours: int = 24) -> list[PressRelease]:
        """指定期間内の新着を取得."""


class PRTimesRSSSource(ProspectingSource):
    """PR タイムズの公式 RSS から取得.

    https://prtimes.jp/index.rdf (公式が提供する RDF/RSS 1.0).
    """

    name = "prtimes_rss"

    def __init__(
        self,
        url: str = PRTIMES_RSS_URL,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.url = url
        self._owned_client = client is None
        self.client = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        """所有しているクライアントをクローズ."""
        if self._owned_client:
            self.client.close()

    def fetch(self, period_hours: int = 24) -> list[PressRelease]:
        """RSS を取得して PressRelease 配列に変換."""
        response = self.client.get(self.url)
        response.raise_for_status()
        releases = self.parse_rss(response.text)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        return [r for r in releases if r.published_at >= cutoff]

    @staticmethod
    def parse_rss(xml_text: str) -> list[PressRelease]:
        """PR タイムズの RDF/RSS 1.0 をパース.

        ベンダー固有の余計なエラー処理はせず、必須要素が欠ける item はスキップ.
        """
        root = ElementTree.fromstring(xml_text)
        items = root.findall("rss:item", _NAMESPACES)
        results: list[PressRelease] = []

        for item in items:
            title_el = item.find("rss:title", _NAMESPACES)
            link_el = item.find("rss:link", _NAMESPACES)
            desc_el = item.find("rss:description", _NAMESPACES)
            date_el = item.find("dc:date", _NAMESPACES)
            creator_el = item.find("dc:creator", _NAMESPACES)
            subject_els = item.findall("dc:subject", _NAMESPACES)

            if title_el is None or link_el is None or date_el is None:
                continue

            published = _parse_iso_or_rfc822(date_el.text or "")
            if published is None:
                continue

            url = (link_el.text or "").strip()
            results.append(
                PressRelease(
                    source_id=url,
                    title=(title_el.text or "").strip(),
                    description=(desc_el.text or "").strip() if desc_el is not None else "",
                    url=url,
                    published_at=published,
                    company=(creator_el.text or "").strip() if creator_el is not None else None,
                    categories=tuple(
                        (el.text or "").strip() for el in subject_els if el.text
                    ),
                )
            )
        return results


def _parse_iso_or_rfc822(value: str) -> datetime | None:
    """ISO8601 または RFC822 形式の日付文字列をパース."""
    value = value.strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
