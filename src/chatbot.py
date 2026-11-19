"""
Module Chatbot RAG Clinique pour le projet UNIDIV.
Implémente la Proposition 1 (recherche sémantique par embedding du prompt utilisateur
dans le corpus scientifique du couple Pays × Thème) tout en préparant les points d'extension
pour les Propositions 2 (`auto_expand_search`) et 3 (`context` libre hors thème prédéfini).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.compare_title_to_prompt import compare_titles_to_prompt
from src.config import MIN_COSINE_SIMILARITY, PROMPT_CHATBOT_CLINIQUE
from src.get_doc_from_site.aggregateur_sources import collecter_toutes_sources
from src.ia_treatment import ia_treatment


def _construire_passage_embedding(article: dict[str, Any]) -> str:
    """Combine le titre et les 600 premiers caractères du résumé (identique à main.py pour partager le cache)."""
    titre = (article.get("title") or "").strip()
    resume = (article.get("abstract") or "").strip()
    if resume:
        return f"{titre}. {resume[:600]}"
    return titre


def _chemin_corpus_local(country: str, context: str) -> Path:
    nom_fichier = lambda x: re.sub(r"[^a-z0-9_-]+", "_", x.strip().lower()).strip("_")
    return Path("data/raw") / f"aggregated_{nom_fichier(country)}_{nom_fichier(context)}.json"


def charger_ou_collecter_corpus(
    country: str,
    context: str,
    force_collect: bool = False,
    max_per_source: int = 25,
) -> list[dict[str, Any]]:
    """
    Charge le corpus d'articles dédupliqués depuis `data/raw/aggregated_<country>_<context>.json`
    s'il est déjà disponible sur le disque (évite tout appel réseau supplémentaire lors du chat),
    ou lance `collecter_toutes_sources` si le fichier n'existe pas encore.
    """
    chemin = _chemin_corpus_local(country, context)
    if not force_collect and chemin.exists():
        try:
            donnees = json.loads(chemin.read_text(encoding="utf-8"))
            articles = donnees.get("articles")
            if isinstance(articles, list) and len(articles) > 0:
                return articles
        except (OSError, ValueError):
            pass

    res = collecter_toutes_sources(
        country=country,
        context=context,
        sujet="",
        max_per_source=max_per_source,
        save_to_disk=True,
    )
    return res.get("articles", [])


def _formater_historique(history: list[dict[str, str]] | None, max_turns: int = 4) -> str:
    """Formate les derniers échanges du chat pour conserver le fil conversationnel."""
    if not history or not isinstance(history, list):
        return ""
    lignes: list[str] = []
    for msg in history[-max_turns:]:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        etiquette = "Médecin" if role == "user" else "Assistant UNIDIV"
        lignes.append(f"- {etiquette} : {content[:400]}")
    if not lignes:
        return ""
    return "\nHistorique récent de la conversation :\n" + "\n".join(lignes) + "\n"


def ask_clinical_chatbot(
    country: str,
    context: str | None,
    question: str,
    history: list[dict[str, str]] | None = None,
    top_k: int = 5,
    min_cosine_similarity: float = MIN_COSINE_SIMILARITY,
    auto_expand_search: bool = False,
) -> dict[str, Any]:
    """
    Répond à une question clinique libre du médecin en utilisant son propre prompt
    pour interroger par similarité cosinus (Nemotron-3-Embed-1B + score HAS) le corpus d'articles.

    Points d'extension prévus :
    - Proposition 2 (`auto_expand_search=True`) : lance une collecte complémentaire ciblée
      sur la question si moins de 2 articles locaux franchissent le seuil cosinus.
    - Proposition 3 (`context=None` ou vide) : utilise la question libre comme contexte de collecte.
    """
    clean_country = (country or "").strip()
    clean_question = (question or "").strip()
    clean_context = (context or "").strip() or clean_question

    if not clean_country or not clean_question:
        raise ValueError("Les paramètres 'country' et 'question' sont obligatoires.")

    # 1. Récupération rapide du corpus d'articles (disque ou collecte)
    articles = charger_ou_collecter_corpus(clean_country, clean_context)

    # 2. Vectorisation & comparaison sémantique avec le prompt de l'utilisateur
    passages = [_construire_passage_embedding(k) for k in articles]
    rec_scores = [
        (k.get("recommendation_score") or {}).get("score_numerique", 20)
        for k in articles
    ]

    # Requête d'embedding centrée sur le prompt de l'utilisateur
    requete_embedding_utilisateur = f"{clean_country} ({clean_context}) : {clean_question}"

    top_positions = compare_titles_to_prompt(
        prompt=requete_embedding_utilisateur,
        titles=passages,
        top_k=top_k,
        recommendation_scores=rec_scores,
        min_cosine_similarity=min_cosine_similarity,
    )

    # Point d'extension Proposition 2 : élargissement automatique si < 2 articles locaux pertinents
    if auto_expand_search and len(top_positions) < 2:
        extra_res = collecter_toutes_sources(
            country=clean_country,
            context=clean_context,
            sujet=clean_question,
            max_per_source=10,
            save_to_disk=False,
        )
        extra_articles = extra_res.get("articles", [])
        if extra_articles:
            from src.get_doc_from_site.aggregateur_sources import dedupliquer_et_fusionner_articles
            articles, _ = dedupliquer_et_fusionner_articles(articles + extra_articles)
            passages = [_construire_passage_embedding(k) for k in articles]
            rec_scores = [
                (k.get("recommendation_score") or {}).get("score_numerique", 20)
                for k in articles
            ]
            top_positions = compare_titles_to_prompt(
                prompt=requete_embedding_utilisateur,
                titles=passages,
                top_k=top_k,
                recommendation_scores=rec_scores,
                min_cosine_similarity=min_cosine_similarity,
            )

    sources_retenues = [articles[idx] for idx in top_positions]

    # 3. Abstention méthodologique anti-hallucination si 0 article ne franchit le seuil
    if not sources_retenues:
        return {
            "country": clean_country,
            "context": clean_context,
            "question": clean_question,
            "answer": (
                "Aucune publication scientifique du corpus collecté pour ce contexte n'a atteint "
                "le seuil de pertinence sémantique requis pour répondre de manière fiable à cette question précise. "
                "Par précaution méthodologique et éthique, l'assistant s'abstient de formuler une réponse sans source."
            ),
            "references": [],
            "abstained": True,
            "corpus_size": len(articles),
        }

    # 4. Préparation du prompt avec la question de l'utilisateur et l'historique éventuel
    historique_bloc = _formater_historique(history)
    prompt_chat_specifique = (
        PROMPT_CHATBOT_CLINIQUE
        .replace("{question}", clean_question)
        .replace("{historique_bloc}", historique_bloc)
    )

    reponse_ia = ia_treatment(
        articles=sources_retenues,
        pays=clean_country,
        contexte=clean_context,
        prompt=prompt_chat_specifique,
    )

    return {
        "country": clean_country,
        "context": clean_context,
        "question": clean_question,
        "answer": reponse_ia or "Impossible de générer une réponse à partir des sources sélectionnées.",
        "references": sources_retenues,
        "abstained": False,
        "corpus_size": len(articles),
    }
