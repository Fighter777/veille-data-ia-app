"""Nettoyage sûr du contenu textuel issu des flux RSS/Atom."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse


TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


class SafeFeedHTMLParser(HTMLParser):
    """Conserve une petite mise en forme sans exécuter le HTML d'une source distante."""

    # Les flux de notes de version utilisent fréquemment des intertitres. Les
    # retirer concatène leur texte au paragraphe précédent et rend la lecture
    # illisible, sans apporter de gain de sécurité.
    allowed_tags = {
        "p", "br", "hr", "div", "ul", "ol", "li",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "strong", "b", "em", "i", "code", "pre", "blockquote", "a",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in self.allowed_tags:
            return
        if tag == "br":
            self.parts.append("<br>")
            return
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"}:
                return
            self.parts.append(f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">')
        else:
            self.parts.append(f"<{tag}>")
        self.open_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.open_tags:
            # Ferme seulement les balises explicitement ouvertes et autorisées.
            while self.open_tags:
                opened = self.open_tags.pop()
                self.parts.append(f"</{opened}>")
                if opened == tag:
                    break

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data))

    def get_html(self) -> str:
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")
        return "".join(self.parts).strip()


def clean_html_text(value: str | None) -> str:
    """Transforme un extrait HTML de flux en texte lisible."""
    if not value:
        return ""
    text = html.unescape(value)
    text = TAG_PATTERN.sub(" ", text)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def sanitize_feed_html(value: str | None) -> str:
    """Préserve une mise en forme minimale et sûre pour l'affichage d'un flux."""
    if not value:
        return ""
    parser = SafeFeedHTMLParser()
    parser.feed(value)
    parser.close()
    return parser.get_html() or clean_html_text(value)
