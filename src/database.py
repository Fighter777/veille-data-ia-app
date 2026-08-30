"""Accès SQLite et persistance de l'application de veille."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd

from src.text_utils import sanitize_feed_html


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "veille.db"

STATUSES = ("À trier", "À lire", "À tester", "Retenu", "Écarté", "À surveiller")
PRIORITIES = ("Basse", "Moyenne", "Haute", "Urgente")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY,
                tool TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                source_type TEXT NOT NULL,
                url TEXT NOT NULL,
                frequency TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                related_projects TEXT,
                last_checked_at TEXT,
                last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                sources_checked INTEGER NOT NULL DEFAULT 0,
                items_found INTEGER NOT NULL DEFAULT 0,
                items_added INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                source_id INTEGER NOT NULL REFERENCES sources(id),
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TEXT,
                fetched_at TEXT NOT NULL,
                detected_version TEXT,
                raw_summary TEXT,
                raw_html TEXT,
                UNIQUE(source_id, url)
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                item_id INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'À trier',
                priority TEXT NOT NULL DEFAULT 'Moyenne',
                related_project TEXT,
                note TEXT,
                decision TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                model TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS translations (
                item_id INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
                model TEXT NOT NULL,
                translation TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                channel TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                UNIQUE(item_id, channel)
            );
            """
        )
        # Migration légère des bases créées avant l'archivage du HTML brut.
        item_columns = {row[1] for row in connection.execute("PRAGMA table_info(items)")}
        if "raw_html" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN raw_html TEXT")


def sanitize_existing_summaries() -> int:
    """Assainit les résumés archivés sans supprimer leur mise en forme autorisée."""
    changed = 0
    with connect() as connection:
        rows = connection.execute("SELECT id, raw_summary FROM items WHERE raw_summary IS NOT NULL").fetchall()
        for row in rows:
            cleaned = sanitize_feed_html(row["raw_summary"])
            if cleaned != row["raw_summary"]:
                connection.execute("UPDATE items SET raw_summary = ? WHERE id = ?", (cleaned, row["id"]))
                changed += 1
    return changed


def sync_sources_from_csv(csv_path: Path) -> int:
    sources = pd.read_csv(csv_path)
    required_columns = {"outil", "categorie", "type_source", "url", "frequence", "actif", "projets_concernes"}
    missing = required_columns - set(sources.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans sources_versions.csv : {', '.join(sorted(missing))}")

    rows = []
    for source in sources.to_dict("records"):
        rows.append(
            (
                source["outil"],
                source["categorie"],
                source["type_source"],
                source["url"],
                source["frequence"],
                int(str(source["actif"]).strip().lower() in {"oui", "true", "1"}),
                source["projets_concernes"],
            )
        )

    with connect() as connection:
        connection.executemany(
            """
            INSERT INTO sources (tool, category, source_type, url, frequency, active, related_projects)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tool) DO UPDATE SET
                category = excluded.category,
                source_type = excluded.source_type,
                url = excluded.url,
                frequency = excluded.frequency,
                active = excluded.active,
                related_projects = excluded.related_projects
            """,
            rows,
        )
    return len(rows)


def add_source(
    *,
    tool: str,
    category: str,
    source_type: str,
    url: str,
    frequency: str,
    related_projects: str,
    active: bool,
) -> None:
    """Ajoute ou met à jour une source saisie depuis l'interface."""
    tool = tool.strip()
    url = url.strip()
    if not tool:
        raise ValueError("Le nom de la source est obligatoire.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("L'URL doit commencer par http:// ou https://.")

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO sources (tool, category, source_type, url, frequency, active, related_projects)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tool) DO UPDATE SET
                category = excluded.category,
                source_type = excluded.source_type,
                url = excluded.url,
                frequency = excluded.frequency,
                active = excluded.active,
                related_projects = excluded.related_projects
            """,
            (tool, category.strip() or "Autre", source_type, url, frequency.strip() or "à définir", int(active), related_projects.strip()),
        )


def create_run() -> int:
    with connect() as connection:
        cursor = connection.execute("INSERT INTO runs (started_at) VALUES (?)", (utc_now(),))
        return int(cursor.lastrowid)


def complete_run(run_id: int, *, sources_checked: int, items_found: int, items_added: int, errors: int) -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE runs
            SET finished_at = ?, sources_checked = ?, items_found = ?, items_added = ?, errors = ?
            WHERE id = ?
            """,
            (utc_now(), sources_checked, items_found, items_added, errors, run_id),
        )


def get_active_sources(automatic_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM sources WHERE active = 1"
    if automatic_only:
        query += " AND source_type IN ('atom_github', 'rss')"
    query += " ORDER BY category, tool"
    with connect() as connection:
        return [dict(row) for row in connection.execute(query).fetchall()]


def mark_source_checked(source_id: int, error: str | None = None) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE sources SET last_checked_at = ?, last_error = ? WHERE id = ?",
            (utc_now(), error, source_id),
        )


def insert_items(source_id: int, items: Iterable[dict[str, str]]) -> int:
    added = 0
    with connect() as connection:
        for item in items:
            existing = connection.execute(
                "SELECT id FROM items WHERE source_id = ? AND url = ?", (source_id, item["url"])
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE items
                    SET title = ?, published_at = COALESCE(?, published_at), fetched_at = ?,
                        detected_version = COALESCE(?, detected_version), raw_summary = COALESCE(?, raw_summary),
                        raw_html = COALESCE(?, raw_html)
                    WHERE id = ?
                    """,
                    (
                        item["title"], item.get("published_at"), utc_now(), item.get("detected_version"),
                        item.get("raw_summary"), item.get("raw_html"), existing["id"],
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO items
                        (source_id, title, url, published_at, fetched_at, detected_version, raw_summary, raw_html)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id, item["title"], item["url"], item.get("published_at"), utc_now(),
                        item.get("detected_version"), item.get("raw_summary"), item.get("raw_html"),
                    ),
                )
                item_id = int(cursor.lastrowid)
                connection.execute(
                    "INSERT INTO evaluations (item_id, updated_at) VALUES (?, ?)",
                    (item_id, utc_now()),
                )
                added += 1
    return added


def get_items(limit: int | None = None) -> pd.DataFrame:
    query = """
        SELECT
            items.id, sources.tool, sources.category, sources.related_projects,
            items.title, items.url, items.published_at, items.fetched_at,
            items.detected_version, items.raw_summary, items.raw_html,
            evaluations.status, evaluations.priority, evaluations.related_project,
            evaluations.note, evaluations.decision, evaluations.updated_at
            , CASE WHEN EXISTS (
                SELECT 1 FROM ai_analyses
                WHERE ai_analyses.item_id = items.id
                  AND ai_analyses.response LIKE '%"statut_propose"%'
            ) THEN 1 ELSE 0 END AS ai_preclassified
        FROM items
        JOIN sources ON sources.id = items.source_id
        JOIN evaluations ON evaluations.item_id = items.id
        ORDER BY COALESCE(items.published_at, items.fetched_at) DESC, items.id DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    with connect() as connection:
        items = pd.read_sql_query(query, connection)
    if items.empty:
        return items
    # Les flux mélangent RFC 822, ISO 8601 et parfois l'absence de date. Un
    # tri SQLite sur ces chaînes donne donc un ordre incohérent.
    published = pd.to_datetime(items["published_at"], utc=True, errors="coerce", format="mixed")
    fetched = pd.to_datetime(items["fetched_at"], utc=True, errors="coerce", format="mixed")
    items["_sort_date"] = published.fillna(fetched)
    items = items.sort_values(["_sort_date", "id"], ascending=[False, False], kind="stable")
    return items.drop(columns="_sort_date").reset_index(drop=True)


def update_evaluation(item_id: int, *, status: str, priority: str, related_project: str, note: str, decision: str) -> None:
    if status not in STATUSES:
        raise ValueError("Statut invalide")
    if priority not in PRIORITIES:
        raise ValueError("Priorité invalide")
    with connect() as connection:
        connection.execute(
            """
            UPDATE evaluations
            SET status = ?, priority = ?, related_project = ?, note = ?, decision = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (status, priority, related_project.strip() or None, note.strip() or None, decision.strip() or None, utc_now(), item_id),
        )


def save_ai_analysis(item_id: int, *, model: str, prompt: str, response: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO ai_analyses (item_id, model, prompt, response, created_at) VALUES (?, ?, ?, ?, ?)",
            (item_id, model, prompt, response, utc_now()),
        )


def get_ai_analyses(item_id: int) -> list[dict[str, str]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT model, prompt, response, created_at FROM ai_analyses WHERE item_id = ? ORDER BY id DESC",
            (item_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_preclassification_candidates(limit: int) -> pd.DataFrame:
    """Éléments encore à trier, sans analyse IA archivée."""
    query = """
        SELECT
            items.id, sources.tool, items.title, items.url, items.published_at,
            items.raw_summary, evaluations.status, evaluations.priority,
            evaluations.related_project, evaluations.note, evaluations.decision
        FROM items
        JOIN sources ON sources.id = items.source_id
        JOIN evaluations ON evaluations.item_id = items.id
        WHERE evaluations.status = 'À trier'
        ORDER BY COALESCE(items.published_at, items.fetched_at) DESC, items.id DESC
        LIMIT ?
    """
    with connect() as connection:
        return pd.read_sql_query(query, connection, params=(limit,))


def get_translation_candidates(limit: int) -> pd.DataFrame:
    """Éléments dont la dernière analyse ne comporte pas encore la traduction RSS."""
    query = """
        SELECT
            items.id, sources.tool, items.title, items.url, items.published_at,
            items.raw_summary, evaluations.status, evaluations.priority,
            evaluations.related_project, evaluations.note, evaluations.decision
        FROM items
        JOIN sources ON sources.id = items.source_id
        JOIN evaluations ON evaluations.item_id = items.id
        WHERE NOT EXISTS (SELECT 1 FROM translations WHERE translations.item_id = items.id)
        ORDER BY COALESCE(items.published_at, items.fetched_at) DESC, items.id DESC
        LIMIT ?
    """
    with connect() as connection:
        return pd.read_sql_query(query, connection, params=(limit,))


def get_latest_preclassifications() -> list[dict[str, Any]]:
    """Dernière proposition IA par élément, sans la confondre avec une décision humaine."""
    query = """
        SELECT analyses.item_id, analyses.model, analyses.response, analyses.created_at,
               items.title, sources.tool
        FROM ai_analyses AS analyses
        JOIN (
            SELECT item_id, MAX(id) AS latest_id FROM ai_analyses GROUP BY item_id
        ) AS latest ON latest.latest_id = analyses.id
        JOIN items ON items.id = analyses.item_id
        JOIN sources ON sources.id = items.source_id
        ORDER BY analyses.created_at DESC
    """
    with connect() as connection:
        return [dict(row) for row in connection.execute(query).fetchall()]


def save_translation(item_id: int, *, model: str, translation: str) -> None:
    with connect() as connection:
        connection.execute(
            """INSERT INTO translations (item_id, model, translation, created_at) VALUES (?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET model = excluded.model, translation = excluded.translation, created_at = excluded.created_at""",
            (item_id, model, translation, utc_now()),
        )


def get_translations() -> dict[int, str]:
    with connect() as connection:
        rows = connection.execute("SELECT item_id, translation FROM translations").fetchall()
    return {int(row["item_id"]): str(row["translation"]) for row in rows}


def notification_already_sent(item_id: int, channel: str) -> bool:
    with connect() as connection:
        return connection.execute(
            "SELECT 1 FROM notifications WHERE item_id = ? AND channel = ?", (item_id, channel)
        ).fetchone() is not None


def record_notification(item_id: int, channel: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO notifications (item_id, channel, sent_at) VALUES (?, ?, ?)",
            (item_id, channel, utc_now()),
        )


def get_runs() -> pd.DataFrame:
    with connect() as connection:
        return pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC LIMIT 30", connection)
