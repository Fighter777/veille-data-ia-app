"""Alertes e-mail SMTP pour les nouvelles pré-classifications."""

from __future__ import annotations

import os
import smtplib
import imaplib
import time
from email.message import EmailMessage

from dotenv import load_dotenv

from src.database import notification_already_sent, record_notification
from src.settings import get_notification_recipients


load_dotenv()


def is_email_configured() -> bool:
    return mail_notifications_enabled() and bool(
        os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM") and (os.getenv("SMTP_TO") or get_notification_recipients())
    )


def mail_notifications_enabled() -> bool:
    return os.getenv("MAIL_NOTIFICATIONS_ENABLED", "0").strip().lower() in {"1", "true", "yes", "oui"}


def send_priority_alert(item: dict[str, str], summary: str) -> bool:
    """Envoie une alerte unique par article. Les erreurs restent non bloquantes."""
    item_id = int(item["id"])
    if not is_email_configured() or notification_already_sent(item_id, "email"):
        return False
    message = EmailMessage()
    message["Subject"] = f"[Veille {item['priority']}] {item['title']}"
    message["From"] = os.environ["SMTP_FROM"]
    recipients = get_notification_recipients() or os.environ.get("SMTP_TO", "")
    message["To"] = recipients.replace("\n", ", ")
    message.set_content(
        f"Outil : {item['tool']}\nPriorité : {item['priority']}\nStatut : {item['status']}\n\n"
        f"Résumé Qwen : {summary}\n\nSource : {item['url']}\n"
    )
    try:
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "25")), timeout=15) as smtp:
            if os.getenv("SMTP_STARTTLS", "false").lower() == "true":
                smtp.starttls()
            username, password = os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD")
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        return False
    archive_sent_message(message)
    record_notification(item_id, "email")
    return True


def archive_sent_message(message: EmailMessage) -> bool:
    """Copie le message envoyé dans le dossier IMAP configuré, sans bloquer l'alerte."""
    if os.getenv("MAIL_ARCHIVE_IMAP_ENABLED", "0").strip() not in {"1", "true", "yes"}:
        return False
    host = os.getenv("MAIL_ARCHIVE_IMAP_HOST")
    username = os.getenv("MAIL_ARCHIVE_IMAP_USERNAME")
    password = os.getenv("MAIL_ARCHIVE_IMAP_PASSWORD")
    if not (host and username and password):
        return False
    port = int(os.getenv("MAIL_ARCHIVE_IMAP_PORT", "143"))
    encryption = os.getenv("MAIL_ARCHIVE_IMAP_ENCRYPTION", "notls").lower()
    mailbox = os.getenv("MAIL_ARCHIVE_IMAP_MAILBOX", "Sent")
    try:
        client = imaplib.IMAP4_SSL(host, port) if encryption == "ssl" else imaplib.IMAP4(host, port)
        if encryption == "starttls":
            client.starttls()
        client.login(username, password)
        client.append(mailbox, "\\Seen", imaplib.Time2Internaldate(time.time()), message.as_bytes())
        client.logout()
        return True
    except (OSError, imaplib.IMAP4.error):
        return False
