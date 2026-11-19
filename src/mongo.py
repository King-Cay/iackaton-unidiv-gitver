from pymongo import MongoClient
from pymongo.errors import PyMongoError
from src.config import MONGO_URI, MONGO_BDD, MONGO_COLLECTION

MONGO_TIMEOUT_MS = 2000


def _get_client() -> MongoClient:
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)


def upload_to_mongo(doc):
    """
    Ajoute le contenu généré pour un couple (country, context) dans MongoDB.
    Si MongoDB est hors ligne, retourne None sans bloquer ni faire planter le pipeline.
    """
    client = _get_client()
    try:
        col = client[MONGO_BDD][MONGO_COLLECTION]
        result = col.insert_one(doc)
        return result.inserted_id
    except PyMongoError:
        return None
    finally:
        client.close()


def get_from_mongo(country, context):
    """
    Récupère depuis MongoDB une synthèse existante pour un couple (country, context).
    Si MongoDB est hors ligne, retourne None immédiatement (après 2s max).
    """
    client = _get_client()
    try:
        col = client[MONGO_BDD][MONGO_COLLECTION]
        doc = col.find_one({
            "country": country,
            "context": context,
        })
        return doc
    except PyMongoError:
        return None
    finally:
        client.close()


def delete_from_mongo(country, context):
    """
    Supprime les entrées MongoDB existantes pour un couple (country, context)
    afin de permettre la régénération complète de la synthèse.
    """
    client = _get_client()
    try:
        col = client[MONGO_BDD][MONGO_COLLECTION]
        result = col.delete_many({
            "country": country,
            "context": context,
        })
        return result.deleted_count
    except PyMongoError:
        return 0
    finally:
        client.close()
