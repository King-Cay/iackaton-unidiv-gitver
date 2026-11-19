from concurrent.futures import ThreadPoolExecutor
from src.get_doc_from_site.aggregateur_sources import collecter_toutes_sources
from src.compare_title_to_prompt import compare_titles_to_prompt
from src.ia_treatment import ia_treatment
from src.config import (
    EMBEDDING_QUERY_FAMILIAUX,
    EMBEDDING_QUERY_INDIVIDUELS,
    EMBEDDING_QUERY_STRUCTURELS,
    MIN_COSINE_SIMILARITY,
    PROMPT_DET_FAMILIAUX,
    PROMPT_DET_INDIVIDUELS,
    PROMPT_DET_STRUCTURELS,
    MONGO_URI,
    MONGO_BDD,
    MONGO_COLLECTION,
)
from src.mongo import get_from_mongo, upload_to_mongo, delete_from_mongo
import json
from pymongo import MongoClient

DETERMINANTS = ["individuels", "familiaux", "structurels"]
EMBEDDING_QUERIES = [
    EMBEDDING_QUERY_INDIVIDUELS,
    EMBEDDING_QUERY_FAMILIAUX,
    EMBEDDING_QUERY_STRUCTURELS,
]
PROMPT = [PROMPT_DET_INDIVIDUELS, PROMPT_DET_FAMILIAUX, PROMPT_DET_STRUCTURELS]


def _construire_passage_embedding(article: dict) -> str:
    """Combine le titre et le début du résumé pour un tri sémantique plus riche."""
    titre = (article.get("title") or "").strip()
    resume = (article.get("abstract") or "").strip()
    if resume:
        return f"{titre}. {resume[:600]}"
    return titre


def main(country,context,force_refresh=False):
    #On cherche si le résultat est dans la bdd mongo
    if not force_refresh:
        doc = get_from_mongo(country,context)
        if doc !=None:
            return doc

    # 1. Collecte multi-sources unique et large (hors de la boucle des 3 déterminants)
    fetch_results = collecter_toutes_sources(country, context, sujet="", max_per_source=25)
    articles = fetch_results["articles"]
    passages = [_construire_passage_embedding(k) for k in articles]
    rec_scores = [
        (k.get("recommendation_score") or {}).get("score_numerique", 20)
        for k in articles
    ]

    top5s = []
    deja_selectionnes: set[int] = set()

    # 2. Sélection séquentielle des Top 5 pour chaque déterminant
    # (préserve le cache d'embeddings du pool et la pénalité anti-redondance inter-axes)
    for i in range(len(DETERMINANTS)):
        requete_semantique = EMBEDDING_QUERIES[i].format(country=country, context=context)

        top_5_positions = compare_titles_to_prompt(
            requete_semantique,
            titles=passages,
            recommendation_scores=rec_scores,
            already_selected_indices=deja_selectionnes,
            min_cosine_similarity=MIN_COSINE_SIMILARITY,
        )
        deja_selectionnes.update(top_5_positions)

        top_5 = [articles[k] for k in top_5_positions]
        top5s.append(top_5)

    # 3. Génération des 3 paragraphes cliniques en parallèle via le LLM
    # (avec abstention automatique si 0 article n'a franchi le seuil de pertinence)
    def _generer_determinant(idx: int) -> str:
        sources_retenues = top5s[idx]
        if not sources_retenues:
            return (
                "Aucune publication scientifique issue des bases interrogées "
                "(PubMed, Europe PMC, OpenAlex, Semantic Scholar, HAL) n'a atteint le seuil "
                "de pertinence requis pour documenter spécifiquement ce déterminant. "
                "Par précaution méthodologique et éthique, aucune synthèse automatique n'est générée sans source."
            )
        resultat_ia = ia_treatment(sources_retenues, country, context, PROMPT[idx])
        return resultat_ia if resultat_ia is not None else ""

    with ThreadPoolExecutor(max_workers=len(DETERMINANTS)) as executor:
        res = list(executor.map(_generer_determinant, range(len(DETERMINANTS))))

    text = {
        "determinant_individuels" : res[0],
        "determinant_familiaux" : res[1],
        "determinant_structurels" : res[2]
            }

    refs = {
        "determinant_individuels" : top5s[0],
        "determinant_familiaux" : top5s[1],
        "determinant_structurels" : top5s[2]      
    }
    
    resultat_def = {
        'country' : country,
        "context" : context,
        "text" : text,
        "references" : refs
    }
    if force_refresh:
        delete_from_mongo(country, context)
    id = upload_to_mongo(resultat_def)
    resultat_def["_id"] = id

    return resultat_def


    

