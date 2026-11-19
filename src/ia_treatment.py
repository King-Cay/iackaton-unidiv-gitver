import os
import re
import requests
from time import time
from keys import API_KEY
from openai import OpenAI


def _nettoyer_reponse_ia(texte: str) -> str:
    """
    Supprime les phrases méta-introductives ou les titres redondants parfois ajoutés
    par le LLM au début du paragraphe (ex: 'Le paragraphe suivant est élaboré selon... :').
    """
    if not texte:
        return ""
    clean = texte.strip()

    # 1. Suppression des phrases d'annonce terminées par ':' en début de texte
    patterns_intro = [
        r"^(?:voici\s+)?le\s+paragraphe\s+(?:suivant|demand[ée])[^:\n]{0,180}:\s*",
        r"^voici\s+(?:une\s+synth[èe]se|un\s+paragraphe|la\s+r[ée]ponse)[^:\n]{0,180}:\s*",
        r"^(?:conform[ée]ment|selon)\s+(?:aux|les)\s+(?:consignes|directives)[^:\n]{0,180}:\s*",
        r"^en\s+s'appuyant\s+sur\s+(?:le\s+contenu\s+des|les)\s+sources[^:\n]{0,180}:\s*",
    ]
    for pat in patterns_intro:
        clean = re.sub(pat, "", clean, flags=re.IGNORECASE).strip()

    # 2. Suppression d'un éventuel titre redondant "Déterminants individuels/familiaux/structurels" en tête
    clean = re.sub(
        r"^(?:#+\s*|\*\*\s*)?d[ée]terminants?\s+(?:individuels?|familiaux|structurels?)\s*(?:\*\*)?\s*[:\-–—]?\s*",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    # 3. Deuxième passe au cas où le titre suivait la phrase d'annonce (ou inversement)
    for pat in patterns_intro:
        clean = re.sub(pat, "", clean, flags=re.IGNORECASE).strip()

    return clean


def _formater_source_pour_prompt(index: int, item) -> str:
    """Formate un article (texte brut ou dictionnaire enrichi du grade HAS) pour le prompt LLM."""
    if isinstance(item, dict):
        abstract = item.get("abstract") or item.get("title") or ""
        rec = item.get("recommendation_score") or {}
        grade = rec.get("grade", "NC")
        niveau = rec.get("niveau_preuve")
        label = rec.get("label", "Niveau non spécifié")
        methode = rec.get("methode_detectee", "Non spécifié")
        niv_str = f" (Niveau {niveau})" if niveau else ""
        return (
            f"--- ARTICLE {index} [Grade HAS : {grade}{niv_str} — {label} | Méthode : {methode}] ---\n"
            f"{abstract}"
        )
    return f"--- ARTICLE {index} ---\n{item}"


def ia_treatment(articles, pays, contexte, prompt):
    # 1. Sécurité : Récupération de la clé API via l'environnement
    api_key =  API_KEY     #os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("La variable d'environnement NVIDIA_API_KEY n'est pas définie.")

    # 2. Injection des variables dans ton prompt
    # On suppose que ton texte 'prompt' contient bien les balises {pays} et {contexte}
    try:
        prompt_formate = prompt.format(pays=pays, contexte=contexte)
    except KeyError as e:
        print(f"Erreur de formatage : le prompt contient une balise inattendue ou il manque la variable {e}")
        return None

    # 3. Formatage structuré des articles (sources) avec leur niveau de preuve HAS
    sources_text = "\n\n".join([_formater_source_pour_prompt(i + 1, article) for i, article in enumerate(articles)])
    
    # 4. Assemblage final (Consignes + Sources)
    final_content = f"{prompt_formate}\n\nVoici les sources à analyser obligatoirement :\n{sources_text}"

    k=2
    if k==1:
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        stream = False

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }


        # 5. Préparation de la requête
        payload = {
            "model": "mistralai/mistral-large-4-1t-a52b",
            "messages": [
                {
                    "role": "user",
                    "content": final_content
                }
            ],
            "max_tokens": 4096,
            "stream": stream,
            "temperature": 0.5,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }

        # 6. Appel à l'API et gestion propre des erreurs
        try:
            response = requests.post(invoke_url, headers=headers, json=payload, stream=stream)
            response.raise_for_status() 
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de l'appel à l'API NVIDIA : {e}")
            
            # Gestion propre de l'objet réponse encapsulé dans l'exception
            if hasattr(e, 'response') and e.response is not None:
                print("Code de statut HTTP :", e.response.status_code)
                print("Détails de la réponse :", e.response.text)
                
            return None
    else:
        client = OpenAI(
            base_url = "https://integrate.api.nvidia.com/v1",
            api_key = API_KEY
        )
        completion = client.chat.completions.create(
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant d'analyse médicale et culturelle. "
                        "Réponds uniquement par le paragraphe demandé, sans phrase d'introduction, "
                        "sans titre et sans conclusion."
                    )
                },
                {
                    "role": "user",
                    "content": final_content
                }
            ],
            temperature=1,
            top_p=0.95,
            max_tokens=16384,
            extra_body={"chat_template_kwargs":{"enable_thinking":False},"reasoning_budget":16384},
            stream=True
        )

        res=[]
        try:
            for chunk in completion:
                if not chunk.choices:
                    continue
                if chunk.choices[0].delta.content is not None:
                    res+=[chunk.choices[0].delta.content]
            return _nettoyer_reponse_ia("".join(res))
        except requests.exceptions.RequestException:
            return None
            


if __name__ == "__main__":
    from config import PROMPT_DET_INDIVIDUELS

    article_1 = """Chez le patient marocain, la perception individuelle de la maladie grave et de la mort est intimement liée à la notion de Mektoub (le destin, ce qui est écrit) et au concept de Qadar (la prédestination divine). Face à l'annonce d'un pronostic vital engagé, l'individu va souvent chercher à démontrer une soumission confiante à la volonté d'Allah. Sur le plan psychologique, cette croyance constitue un mécanisme de coping très puissant contre l'angoisse de mort. Le médecin occidental ne doit pas interpréter cette acceptation religieuse comme du fatalisme passif, un déni de gravité ou un refus de se battre contre la maladie, mais comme une ressource spirituelle qui aide le patient à trouver un sens à sa souffrance et à sa fin de vie."""
    article_2 = """Pour le patient marocain, particulièrement s'il est âgé ou très pratiquant, le rapport au corps en milieu hospitalier est régi par des règles strictes de pudeur (Awrah). À l'approche de la mort, cette préoccupation individuelle a tendance à s'exacerber. Le patient peut redouter les examens nécessitant une nudité totale ou les toilettes mortuaires réalisées par du personnel du sexe opposé. Il est essentiel pour la tranquillité d'esprit du mourant de savoir que son corps sera respecté selon les rites islamiques (le Ghusl, ou lavage rituel) après son décès. Garantir au patient que sa pudeur sera préservée jusqu'au bout, et si possible par des soignants de même sexe, diminue drastiquement l'anxiété liée à l'hospitalisation en fin de vie."""
    article_3 = """La gestion individuelle des émotions lors d'un deuil au Maroc est traversée par un paradoxe entre l'idéal religieux et la pratique culturelle. D'un côté, l'islam enjoint l'individu à faire preuve de Sabr (endurance, patience stoïque) face à la perte, considérant que les pleurs excessifs et les lamentations bruyantes peuvent troubler le repos du défunt. Le patient endeuillé peut donc s'efforcer de contenir ses larmes en présence du personnel médical pour montrer sa force spirituelle. Cependant, les décharges émotionnelles intenses, les pleurs collectifs et parfois les cris sont culturellement très fréquents et tolérés dans les premiers instants du choc, agissant comme une catharsis individuelle. Le clinicien doit naviguer entre ces deux extrêmes sans médicaliser (par des calmants) ce qui relève d'une expression culturelle normale de la douleur."""

    articles = [article_1,article_2,article_3]
    start = time()
    res = ia_treatment(articles,"Maroc","Mort et deuil",PROMPT_DET_INDIVIDUELS)
    print(res)
    stop = time()
    print("\n\n\n")
    print(stop - start)
    """
    if res is not None:
        try:
            # L'API Mistral/NVIDIA renvoie le texte dans ce chemin précis :
            texte_genere = res["choices"][0]["message"]["content"]
            
            # Ajout de l'encoding="utf-8" obligatoire pour les accents français
            with open("res.txt", "w", encoding="utf-8") as f:
                f.write(texte_genere)
                
            print("Résultat sauvegardé avec succès dans res.txt")
            
        except (KeyError, IndexError) as e:
            # Si l'API renvoie un JSON valide mais pas au format attendu (ex: blocage de sécurité)
            print("Erreur lors de l'extraction du texte. Voici ce que l'API a répondu :")
            print(res)"""