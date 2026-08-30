"""Client facultatif pour un serveur local Qwen compatible OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from src.text_utils import clean_html_text


load_dotenv()


def is_configured() -> bool:
    return bool(os.getenv("QWEN_BASE_URL") and os.getenv("QWEN_API_KEY") and os.getenv("QWEN_MODEL"))


def analyse_item(item: dict[str, Any]) -> tuple[str, str, str]:
    """Retourne le modèle, le prompt et la réponse brute ; ne décide jamais à la place de l'utilisateur."""
    if not is_configured():
        raise RuntimeError("Qwen n'est pas configuré. Copiez .env.example vers .env puis renseignez les valeurs.")

    model = os.environ["QWEN_MODEL"]
    prompt = f"""Tu assistes une veille technologique Data/IA. Analyse l'élément ci-dessous sans inventer de faits.

Outil ou modèle : {item['tool']}
Titre : {item['title']}
Date publiée : {item.get('published_at') or 'non précisée'}
Résumé source : {item.get('raw_summary') or 'non disponible'}
URL : {item['url']}

Réponds exclusivement en français et en JSON strict avec les clés :
- resume_factuel : maximum 90 mots, uniquement à partir du contenu fourni ;
- tags : liste courte ;
- projets_impactes : liste de projets potentiellement concernés ;
- statut_propose : obligatoirement l'une de ces valeurs : À lire, À tester, À surveiller ou Écarté ;
- priorite_proposee : Basse, Moyenne, Haute ou Urgente ;
- raison : une phrase ;
- verification_humaine : une question ou un point à contrôler avant décision.

Cette réponse est une proposition : elle ne doit jamais constituer une décision automatique."""

    client = OpenAI(base_url=os.environ["QWEN_BASE_URL"], api_key=os.environ["QWEN_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Tu produis exclusivement du JSON valide."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=700,
        # Qwen consommait auparavant toute la limite dans son raisonnement
        # interne, sans jamais émettre le JSON final dans `content`.
        # llama.cpp transmet cette option au template de chat Qwen.
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(
            "Qwen n'a pas produit de réponse finale. Vérifiez le mode thinking ou augmentez la limite de tokens du serveur."
        )
    # Vérification non bloquante : la réponse brute reste archivée même si le modèle ne respecte pas le JSON.
    try:
        json.loads(content)
    except json.JSONDecodeError:
        pass
    return model, prompt, content


def translate_excerpt(item: dict[str, Any]) -> tuple[str, str]:
    """Traduit uniquement l'extrait RSS, séparément de la pré-classification."""
    if not is_configured():
        raise RuntimeError("Qwen n'est pas configuré.")
    prompt = f"""Traduis fidèlement en français l'extrait RSS ci-dessous.
Conserve les faits, les noms de produits et les numéros de version. Réponds uniquement par la traduction, sans commentaire. Si l'extrait est long, produis une traduction condensée de 180 mots maximum.

Outil : {item['tool']}
Extrait RSS : {clean_html_text(item.get('raw_summary', ''))}"""
    client = OpenAI(base_url=os.environ["QWEN_BASE_URL"], api_key=os.environ["QWEN_API_KEY"])
    response = client.chat.completions.create(
        model=os.environ["QWEN_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=900,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Qwen n'a pas produit de traduction finale.")
    return os.environ["QWEN_MODEL"], content.strip()
