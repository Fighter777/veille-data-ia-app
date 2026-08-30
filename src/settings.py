"""Préférences locales de l'interface, hors base de veille."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "data" / "app_settings.json"


def get_auto_preclassify() -> bool:
    """Lit le réglage persistant, avec un défaut sûr à False."""
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return bool(data.get("auto_preclassify", False))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False


def _load_settings() -> dict[str, bool]:
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
