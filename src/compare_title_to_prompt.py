import os
import numpy as np
from openai import OpenAI
from keys import API_KEY

NUMBER_OF_SELECTED_ARTICLES = 5

# Cache mémoire léger pour éviter de recalculer 3 fois les embeddings du même pool d'articles
# lors de la boucle sur les 3 déterminants (Individuel, Familial, Structurel).
_PASSAGES_EMBEDDING_CACHE: dict[tuple[str, ...], np.ndarray] = {}


def compare_titles_to_prompt(
    prompt: str, 
    titles: list[str], 
    top_k: int = NUMBER_OF_SELECTED_ARTICLES,
    recommendation_scores: list[float] | None = None,
    already_selected_indices: set[int] | None = None,
    redundancy_penalty: float = 0.15,
    min_cosine_similarity: float | None = None,
) -> list[int]:
    if not titles:
        return []

    api_key = API_KEY

    if not api_key:
        raise ValueError("La variable d'environnement NVIDIA_API_KEY n'est pas définie.")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    model_name = "nvidia/nemotron-3-embed-1b"

    # 1. Embedding du prompt spécifique au déterminant (recherche asymétrique : input_type="query")
    prompt_resp = client.embeddings.create(
        input=[prompt],
        model=model_name,
        encoding_format="float",
        extra_body={"input_type": "query", "truncate": "END"}
    )
    prompt_emb = np.array(prompt_resp.data[0].embedding)

    # 2. Embeddings des passages/titres (input_type="passage") avec mise en cache du pool
    cache_key = tuple(titles)
    if cache_key in _PASSAGES_EMBEDDING_CACHE:
        titles_emb = _PASSAGES_EMBEDDING_CACHE[cache_key]
    else:
        titles_resp = client.embeddings.create(
            input=titles,
            model=model_name,
            encoding_format="float",
            extra_body={"input_type": "passage", "truncate": "END"}
        )
        titles_emb = np.array([item.embedding for item in titles_resp.data])
        if len(_PASSAGES_EMBEDDING_CACHE) > 16:
            _PASSAGES_EMBEDDING_CACHE.clear()
        _PASSAGES_EMBEDDING_CACHE[cache_key] = titles_emb

    # 3. Similarité cosinus entre le prompt du déterminant et chaque article
    norms = np.linalg.norm(titles_emb, axis=1) * np.linalg.norm(prompt_emb)
    cosine_scores = np.dot(titles_emb, prompt_emb) / np.where(norms == 0, 1e-10, norms)

    # 4. Pondération optionnelle avec le score de recommandation scientifique (HAS)
    if recommendation_scores is not None and len(recommendation_scores) == len(titles):
        rec_norm = np.clip(np.array(recommendation_scores, dtype=float) / 100.0, 0.0, 1.0)
        scores = 0.80 * cosine_scores + 0.20 * rec_norm
    else:
        scores = cosine_scores.copy()

    # 5. Pénalité de redondance inter-déterminants pour diversifier les sources sélectionnées
    if already_selected_indices:
        for idx in already_selected_indices:
            if 0 <= idx < len(scores):
                scores[idx] -= redundancy_penalty

    # 6. Filtrage par seuil minimal sur la similarité cosinus pure (évite les articles hors-sujet)
    ranked_indices = np.argsort(scores)[::-1].tolist()
    if min_cosine_similarity is not None:
        ranked_indices = [
            idx for idx in ranked_indices
            if float(cosine_scores[idx]) >= float(min_cosine_similarity)
        ]

    # 7. Indices des top_k meilleurs scores survivants (de 0 à top_k articles)
    top_positions = ranked_indices[:top_k]

    return top_positions


