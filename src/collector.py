"""Collecte des flux Atom/RSS configurés pour la veille."""

from __future__ import annotations

import re
from typing import Any

import feedparser

from src.text_utils import sanitize_feed_html


VERSION_PATTERN = re.compile(r"(?:v(?:ersion)?\s*)?(\d+(?:\.\d+){1,3}(?:[-+._][\w.-]+)?)", re.IGNORECASE)


def fetch_feed(source: dict[str, Any], max_entries: int = 10) -> list[dict[str, str]]:
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
        raw_html = str(entry.get("summary", entry.get("description", "")))
        summary = sanitize_feed_html(raw_html)
        match = VERSION_PATTERN.search(title)
        items.append(
            {
                "title": title,
                "url": link,
                "published_at": str(entry.get("published", entry.get("updated", ""))),
                "detected_version": match.group(1) if match else "",
                "raw_summary": summary,
                "raw_html": raw_html,
            }
        )
    return items
