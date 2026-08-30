"""Client facultatif pour un serveur d'IA local compatible OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from src.settings import get_priority_guidelines
from src.text_utils import clean_html_text


load_dotenv()


def _setting(name: str) -> str:
    """Privilégie LLM_* et accepte QWEN_* le temps de migrer les installations."""
    return os.getenv(f"LLM_{name}") or os.getenv(f"QWEN_{name}") or ""


def _extra_body() -> dict[str, Any] | None:
    raw = os.getenv("LLM_EXTRA_BODY_JSON", "").strip()
    if not raw:
        # Compatibilité avec l'ancienne configuration QWEN_* utilisée par
        # llama.cpp : elle désactivait explicitement le raisonnement interne.
        if os.getenv("QWEN_MODEL"):
            return {"chat_template_kwargs": {"enable_thinking": False}}
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("LLM_EXTRA_BODY_JSON doit contenir un objet JSON valide.") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM_EXTRA_BODY_JSON doit contenir un objet JSON.")
    return parsed


def is_configured() -> bool:
    return bool(_setting("BASE_URL") and _setting("API_KEY") and _setting("MODEL"))


def _client() -> OpenAI:
    if not is_configured():
        raise RuntimeError("L'IA locale n'est pas configurée. Renseignez les variables LLM_* dans .env.")
    return OpenAI(base_url=_setting("BASE_URL"), api_key=_setting("API_KEY"))


def _completion(*, prompt: str, temperature: float, max_tokens: int, system_prompt: str | None = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    parameters: dict[str, Any] = {
        "model": _setting("MODEL"),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_body := _extra_body():
        parameters["extra_body"] = extra_body
    response = _client().chat.completions.create(**parameters)
    return response.choices[0].message.content or ""


def analyse_item(item: dict[str, Any]) -> tuple[str, str, str]:
    """Retourne modèle, prompt et réponse brute ; la décision reste humaine."""
    prompt = f"""Tu assistes une veille technologique Data/IA. Analyse l'élément ci-dessous sans inventer de faits.

Outil ou modèle : {item['tool']}
Titre : {item['title']}
Date publiée : {item.get('published_at') or 'non précisée'}
Résumé source : {item.get('raw_summary') or 'non disponible'}
URL : {item['url']}

Applique strictement cette grille de priorités définie par l'administration :
{get_priority_guidelines()}

Réponds exclusivement en français et en JSON strict avec les clés :
- resume_factuel : maximum 90 mots, uniquement à partir du contenu fourni ;
- tags : liste courte ;
- projets_impactes : liste de projets potentiellement concernés ;
- statut_propose : obligatoirement l'une de ces valeurs : À lire, À tester, À surveiller ou Écarté ;
- priorite_proposee : Basse, Moyenne, Haute ou Urgente ;
- raison : une phrase ;
- verification_humaine : une question ou un point à contrôler avant décision.

Cette réponse est une proposition : elle ne doit jamais constituer une décision automatique."""
    content = _completion(prompt=prompt, system_prompt="Tu produis exclusivement du JSON valide.", temperature=0.2, max_tokens=700)
    if not content:
        raise RuntimeError("L'IA locale n'a pas produit de réponse finale. Vérifiez le modèle et sa configuration.")
    try:
        json.loads(content)
    except json.JSONDecodeError:
        pass
    return _setting("MODEL"), prompt, content


def translate_excerpt(item: dict[str, Any]) -> tuple[str, str]:
    """Traduit uniquement l'extrait RSS, séparément de la pré-classification."""
    prompt = f"""Traduis fidèlement en français l'extrait RSS ci-dessous.
Conserve les faits, les noms de produits et les numéros de version. Réponds uniquement par la traduction, sans commentaire. Si l'extrait est long, produis une traduction condensée de 180 mots maximum.

Outil : {item['tool']}
Extrait RSS : {clean_html_text(item.get('raw_summary', ''))}"""
    content = _completion(prompt=prompt, temperature=0.1, max_tokens=900)
    if not content:
        raise RuntimeError("L'IA locale n'a pas produit de traduction finale.")
    return _setting("MODEL"), content.strip()
