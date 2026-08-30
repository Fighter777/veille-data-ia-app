"""Préférences locales de l'interface, hors base de veille."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "data" / "app_settings.json"

DEFAULT_PRIORITY_CRITERIA = {
    "Urgente": "Faille critique, compromission, indisponibilité majeure, rupture de compatibilité ou action immédiate nécessaire.",
    "Haute": "Changement important susceptible d'impacter directement un projet, un outil en production ou une décision à court terme.",
    "Moyenne": "Évolution utile à examiner ou tester, sans action immédiate ni impact avéré.",
    "Basse": "Information générale, maintenance mineure, annonce ou nouveauté à faible impact pour les projets suivis.",
}


def get_auto_preclassify() -> bool:
    """Lit le réglage persistant, avec un défaut sûr à False."""
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return bool(data.get("auto_preclassify", False))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False


def _load_settings() -> dict[str, object]:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_setting(key: str, enabled: bool) -> None:
    settings = _load_settings()
    settings[key] = bool(enabled)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2) + "\n",
        encoding="utf-8",
    )


def save_auto_preclassify(enabled: bool) -> None:
    """Conserve la préférence d'automatisation locale."""
    _save_setting("auto_preclassify", enabled)


def get_render_raw_html() -> bool:
    return bool(_load_settings().get("render_raw_html", False))


def save_render_raw_html(enabled: bool) -> None:
    _save_setting("render_raw_html", enabled)


def get_notification_priorities() -> list[str]:
    values = _load_settings().get("notification_priorities", ["Urgente"])
    return [str(value) for value in values] if isinstance(values, list) else ["Urgente"]


def save_notification_priorities(priorities: list[str]) -> None:
    settings = _load_settings()
    settings["notification_priorities"] = priorities
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def get_notification_recipients() -> str:
    return str(_load_settings().get("notification_recipients", ""))


def save_notification_recipients(recipients: str) -> None:
    settings = _load_settings()
    settings["notification_recipients"] = recipients.strip()
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def get_watch_start_date() -> str:
    return str(_load_settings().get("watch_start_date", ""))


def save_watch_start_date(value: str) -> None:
    settings = _load_settings()
    settings["watch_start_date"] = value
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def get_admin_notification_priorities() -> list[str]:
    values = _load_settings().get("admin_notification_priorities", ["Urgente"])
    return [str(value) for value in values] if isinstance(values, list) else ["Urgente"]


def save_admin_notification_priorities(priorities: list[str]) -> None:
    settings = _load_settings()
    settings["admin_notification_priorities"] = priorities
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def get_admin_notification_recipients() -> str:
    return str(_load_settings().get("admin_notification_recipients", ""))


def save_admin_notification_recipients(recipients: str) -> None:
    settings = _load_settings()
    settings["admin_notification_recipients"] = recipients.strip()
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def get_ai_enabled() -> bool:
    """Conserve l'état de la fonctionnalité sans casser une installation existante."""
    settings = _load_settings()
    return bool(settings.get("ai_enabled", settings.get("qwen_enabled", True)))


def save_ai_enabled(enabled: bool) -> None:
    _save_setting("ai_enabled", enabled)


def get_priority_criteria() -> dict[str, str]:
    """Retourne une règle explicite pour chacun des quatre niveaux."""
    saved = _load_settings().get("priority_criteria")
    if not isinstance(saved, dict):
        return DEFAULT_PRIORITY_CRITERIA.copy()
    return {
        level: str(saved.get(level, DEFAULT_PRIORITY_CRITERIA[level])).strip() or DEFAULT_PRIORITY_CRITERIA[level]
        for level in DEFAULT_PRIORITY_CRITERIA
    }


def save_priority_criteria(criteria: dict[str, str]) -> None:
    settings = _load_settings()
    settings["priority_criteria"] = {
        level: str(criteria.get(level, "")).strip() or DEFAULT_PRIORITY_CRITERIA[level]
        for level in DEFAULT_PRIORITY_CRITERIA
    }
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def get_priority_guidelines() -> str:
    """Formate les critères pour leur insertion dans le prompt de l'IA."""
    criteria = get_priority_criteria()
    return "\n".join(f"- {level} : {criteria[level]}" for level in ("Urgente", "Haute", "Moyenne", "Basse"))
