"""Collecte des flux Atom/RSS configurés pour la veille."""

from __future__ import annotations

import re
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from src.text_utils import sanitize_feed_html


VERSION_PATTERN = re.compile(r"(?:v(?:ersion)?\s*)?(\d+(?:\.\d+){1,3}(?:[-+._][\w.-]+)?)", re.IGNORECASE)


def _entry_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return parsedate_to_datetime(value).date()
        except (TypeError, ValueError):
            return None


def fetch_feed(source: dict[str, Any], max_entries: int = 10, since: date | None = None) -> list[dict[str, str]]:
    """Récupère les nouveautés d'un flux Atom ou RSS configuré."""
    feed = feedparser.parse(source["url"])
    if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
        detail = getattr(feed, "bozo_exception", "flux invalide")
        raise RuntimeError(str(detail))

    items: list[dict[str, str]] = []
    for entry in feed.entries[:max_entries]:
        title = str(entry.get("title", "Sans titre")).strip()
        link = str(entry.get("link", "")).strip()
        if not title or not link:
            continue
        published_at = str(entry.get("published", entry.get("updated", "")))
        if since and (_entry_date(published_at) is None or _entry_date(published_at) < since):
            continue
        raw_html = str(entry.get("summary", entry.get("description", "")))
        summary = sanitize_feed_html(raw_html)
        match = VERSION_PATTERN.search(title)
        items.append(
            {
                "title": title,
                "url": link,
                "published_at": published_at,
                "detected_version": match.group(1) if match else "",
                "raw_summary": summary,
                "raw_html": raw_html,
            }
        )
    return items
