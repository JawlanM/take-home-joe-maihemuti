"""MongoDB connection. The only place a MongoClient is created."""

from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import settings


def get_candidates_collection() -> Collection:
    # tz_aware=True so datetimes come back as UTC-aware, matching what we store.
    client = MongoClient(settings.mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    return client[settings.mongodb_db]["candidates"]
