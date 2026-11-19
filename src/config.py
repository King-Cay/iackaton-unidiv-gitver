MONGO_URI = "mongodb://127.0.0.1:27017/"
MONGO_BDD = "bdd"
MONGO_COLLECTION = "documents"

# Seuil minimal de similarité cosinus (entre la requête du déterminant et le passage Titre+Résumé)
# en dessous duquel un article est écarté même s'il figure dans le Top 5, afin d'éviter le hors-sujet.
MIN_COSINE_SIMILARITY = 0.28

# Requêtes sémantiques riches pour orienter le modèle d'embeddings (Nemotron-3-Embed-1B)
# sur chacun des 3 déterminants à partir d'un pool unique d'articles collectés.
EMBEDDING_QUERY_INDIVIDUELS = (
    "Individual and personal determinants of {context} in {country}: "
    "patient personal beliefs, lived experience, psychological coping, emotions, "
    "body modesty, spirituality, self-perception of illness, stigma, "
    "représentations individuelles, croyances personnelles, vécu psychologique et pudeur du patient."
)

EMBEDDING_QUERY_FAMILIAUX = (
    "Family and kinship determinants of {context} in {country}: "
    "role of family, relatives, spouse, parents, elders, caregivers, gender roles, "
    "collective medical decision-making, family support, household dynamics, "
    "rôle de la famille, entourage, solidarité familiale et prise de décision collective."
)

EMBEDDING_QUERY_STRUCTURELS = (
    "Structural, societal and healthcare system determinants of {context} in {country}: "
    "healthcare system organization, access to care, financial or geographical barriers, "
    "public health policy, hospital infrastructure, socio-economic context, traditional vs biomedical care, "
    "système de santé, barrières d'accès aux soins, contexte socio-économique et institutionnel."
)

PROMPT_DET_INDIVIDUELS = """
Je suis un médécin français qui reçois un patient que vient de {pays} avec un problème dans  le contexte de {contexte}.
je veux que tu me génère un paragraphe sur les coutumes ou pratiques médicales ou qui pourrait être intéressant à connaître pour moi, le médécin, afin de mieux comprendre mon patient.
voici tes consignes:
_ Le paragraphe porte sur les déterminants individuels : il doit parler de comment le patient, avec sa culture et son vécu, pourrait percevoir le contexte ({contexte}) dont on parle.
_ Commence directement par le contenu clinique et culturel : n'écris AUCUNE phrase d'introduction (ne dis jamais "Le paragraphe suivant...", "Voici le paragraphe...", ni le titre "Déterminants individuels").
_ Je veux que tu restes respecteux du patient et je veux que tu respecte la convention des droits de l'homme à la lettre. Pas d'attaque sur les cultures ou des mots dénigrateurs.
_Je veux que tout ton travail proviennent de sources qui vont suivre et uniquement d'elles. Cependant certaines sources pourraient ne pas contenir d'informations importantes et donc tu pourra les ignorer.
"""
PROMPT_DET_FAMILIAUX = """
Je suis un médécin français qui reçois un patient que vient de {pays} avec un problème dans  le contexte de {contexte}.
je veux que tu me génère un paragraphe sur les coutumes ou pratiques médicales ou qui pourrait être intéressant à connaître pour moi, le médécin, afin de mieux comprendre mon patient.
voici tes consignes:
_ Le paragraphe porte sur les déterminants familiaux : il doit parler de comment la famille du patient, avec leur culture potentielle, pourrait percevoir le contexte ({contexte}) dont on parle.
_ Commence directement par le contenu clinique et culturel : n'écris AUCUNE phrase d'introduction (ne dis jamais "Le paragraphe suivant...", "Voici le paragraphe...", ni le titre "Déterminants familiaux").
_ Je veux que tu restes respecteux du patient et je veux que tu respecte la convention des droits de l'homme à la lettre. Pas d'attaque sur les cultures ou des mots dénigrateurs.
_Je veux que tout ton travail proviennent de sources qui vont suivre et uniquement d'elles. Cependant certaines sources pourraient ne pas contenir d'informations importantes et donc tu pourra les ignorer.
"""
PROMPT_DET_STRUCTURELS = """
Je suis un médécin français qui reçois un patient que vient de {pays} avec un problème dans  le contexte de {contexte}.
je veux que tu me génère un paragraphe sur les coutumes ou pratiques médicales ou qui pourrait être intéressant à connaître pour moi, le médécin, afin de mieux comprendre mon patient.
voici tes consignes:
_ Le paragraphe porte sur les déterminants structurels : il doit parler de comment la société d'où vient le patient pourrait percevoir le contexte ({contexte}) dont on parle.
_ Commence directement par le contenu clinique et culturel : n'écris AUCUNE phrase d'introduction (ne dis jamais "Le paragraphe suivant...", "Voici le paragraphe...", ni le titre "Déterminants structurels").
_ Je veux que tu restes respecteux du patient et je veux que tu respecte la convention des droits de l'homme à la lettre. Pas d'attaque sur les cultures ou des mots dénigrateurs.
_Je veux que tout ton travail proviennent de sources qui vont suivre et uniquement d'elles. Cependant certaines sources pourraient ne pas contenir d'informations importantes et donc tu pourra les ignorer.
"""

PROMPT_CHATBOT_CLINIQUE = """
Je suis un médecin français qui consulte un patient originaire de {pays} dans le contexte médical suivant : {contexte}.
Voici ma question clinique précise : "{question}"
{historique_bloc}
Voici tes consignes strictes :
_ Réponds directement, de façon claire, synthétique et opérationnelle pour ma consultation médicale.
_ Commence directement par la réponse : n'écris AUCUNE phrase d'introduction méta (ne dis jamais "Le paragraphe suivant...", "Voici la réponse...", ni "D'après les sources fournies...").
_ Reste profondément respectueux du patient, de sa culture et de la convention des droits de l'homme. Aucune généralisation abusive ni terme dénigrant.
_ Appuie-toi EXCLUSIVEMENT sur les sources scientifiques qui vont suivre (annotées de leur Grade HAS). Si ces sources ne couvrent qu'une partie de ma question, réponds sur ce qui est documenté et précise avec honnêteté clinique ce qui n'est pas précisé dans les sources.
"""


PROMPT = """
Je suis un médécin français qui reçois un patient que vient de {pays} avec un problème dans  le contexte de {contexte}.
je veux que tu me génère un document de trois paragraphes sur les coutumes ou pratiques médicales ou qui pourrait être intéressant à connaître pour moi, le médécin, afin de mieux comprendre mon patient.
voici tes consignes:
_ Les trois paragraphes ont chacun un angle qui sont dans l'ordre : les déterminants individuels , les déterminants familiaux et les déterminants structurels.
_ Je veux que tu restes respecteux du patient et je veux que tu respecte la convention des droits de l'homme à la lettre. Pas d'attaque sur les cultures ou des mots dénigrateurs.
_Je veux que tout ton travail proviennent de sources que voici : 
    _TMGL de L’OMS (traditionnal medicine global library)
	_Food and agriculture organization of the united nations  
	_Pubmed 
	_Les bibliothèques universitaires : Sorbonne, Londres, Strasbourg, Biu paris medica,  etc… 
	_Orphanet pour la génétique
	_Institut Pasteur pour l’infectiologie
	_Ministère des affaires étrangères pour le contexte géopolitique et les maladies 
	_the international library of essays in anthropology  
	_La Comede – Comité pour la santé des exilés  
	_L’UQAM  https://classiques.uqam.ca/contemporains/anthropologie_medicale/index.html   
	_Ordre des médecins de chaque pays 
    _revues Mémoires (Centre Primo Lévi)
	_revue Rhizome  et journal des psychologues (Cairn)
	_ AnthroSource 
	_JSTOR https://www.jstor.org/
	_Oriv --- réseau RECI https://biblio.reseau-reci.org/
	_Revue epidemiology
	_https://bib.cnrs.fr/
	_couperin.org
	_google scholar 
	_semantic scholar 
	_Anthropological Index Online https://aio.therai.org.uk/advanced-search
    _ArkeOpen
    _Biodiversity
_Je veux que tu cites absolument chaque source que tu utilise dans l'ordre avec son url et je veux que tu donnes à chaque source un score de fiabilité.


"""
PROMPT_AMELIORE = """
Agis en tant que médecin français recevant un patient originaire de {pays}, qui consulte pour un problème dans le contexte suivant : {contexte}.

Génère un document de synthèse clinique et anthropologique de trois paragraphes pour m'aider, en tant que médecin, à mieux appréhender les pratiques, coutumes ou représentations médicales de ce patient.

Structure exigée :

Paragraphe 1 : Les déterminants individuels (représentation de la maladie, croyances personnelles).

Paragraphe 2 : Les déterminants familiaux (rôle de l'entourage, hiérarchie dans la prise de décision médicale).

Paragraphe 3 : Les déterminants structurels (rapport au système de santé dans le pays d'origine, contexte géopolitique, barrières d'accès).

Contraintes éthiques et de ton :

Adopte une approche strictement clinique, empathique et respectueuse.

Respecte scrupuleusement les droits de l'homme. Aucune généralisation abusive, aucun jugement de valeur ni terme dénigrant sur la culture d'origine.

Contraintes épistémologiques et sources :

Appuie ton analyse exclusivement sur les connaissances consensuelles issues de la médecine tropicale, de l'anthropologie médicale et de l'infectiologie (en t'inspirant des standards de l'OMS, de la FAO, d'Orphanet, de l'Institut Pasteur, du Centre Primo Lévi et de la littérature académique type PubMed, JSTOR ou Cairn).

À la fin du document, cite les 2 ou 3 concepts scientifiques, anthropologiques ou médicaux majeurs que tu as mobilisés, en indiquant quel type d'institution ou de littérature (ex: anthropologie médicale, épidémiologie) les documente habituellement. Si tu cites des études, précise qu'il s'agit de références générales et non de liens directs.
"""